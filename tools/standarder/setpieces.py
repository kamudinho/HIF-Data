import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
from PIL import Image
from io import BytesIO
from mplsoccer import Pitch, VerticalPitch
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "2mb332vncy4450vu14paj8844" 
PLAYER_FILE = 'data/players/1div_overskrivning.csv'

@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def universal_decode(text):
    if not isinstance(text, str): return text
    try: return text.encode('latin1').decode('utf-8')
    except: return text

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    sql = (
        "WITH BaseEvents AS ("
        "    SELECT "
        "        e.EVENT_OPTAUUID, e.MATCH_OPTAUUID, e.EVENT_EVENTID,"
        "        e.EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,"
        "        e.EVENT_TYPEID,"
        "        TRIM(e.PLAYER_OPTAUUID) AS PLAYER_UUID,"
        "        e.PLAYER_NAME,"
        "        e.EVENT_X, e.EVENT_Y,"
        "        LEAD(TRIM(e.PLAYER_OPTAUUID), 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_UUID,"
        "        LEAD(e.PLAYER_NAME, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_NAME,"
        "        LEAD(e.EVENT_CONTESTANT_OPTAUUID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_TEAM,"
        "        LEAD(e.EVENT_TYPEID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_TYPE,"
        "        LEAD(e.EVENT_TYPEID, 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P2_TYPE,"
        "        LEAD(e.EVENT_TYPEID, 3) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P3_TYPE"
        "    FROM " + DB + ".OPTA_EVENTS e"
        "    WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '" + LIGA_UUID + "'"
        "),"
        "Quals AS ("
        "    SELECT "
        "        EVENT_OPTAUUID,"
        "        MAX(CASE WHEN QUALIFIER_QID = 107 THEN 'Indkast'"
        "                 WHEN QUALIFIER_QID = 6 THEN 'Hjørnespark'"
        "                 WHEN QUALIFIER_QID = 5 THEN 'Frispark' END) AS TYPE_NAVN,"
        "        MAX(CASE WHEN QUALIFIER_QID = 140 THEN QUALIFIER_VALUE END) AS ENDX,"
        "        MAX(CASE WHEN QUALIFIER_QID = 141 THEN QUALIFIER_VALUE END) AS ENDY"
        "    FROM " + DB + ".OPTA_QUALIFIERS"
        "    WHERE QUALIFIER_QID IN (5, 6, 107, 140, 141)"
        "    GROUP BY EVENT_OPTAUUID"
        ") "
        "SELECT b.*, q.TYPE_NAVN, q.ENDX, q.ENDY "
        "FROM BaseEvents b "
        "JOIN Quals q ON b.EVENT_OPTAUUID = q.EVENT_OPTAUUID "
        "WHERE q.TYPE_NAVN IS NOT NULL"
    )
    
    try:
        df = conn.query(sql)
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [c.upper() for c in df.columns]
        df['PLAYER_NAME'] = df['PLAYER_NAME'].apply(universal_decode)
        df['P1_NAME'] = df['P1_NAME'].apply(universal_decode)
        
        try:
            df_lookup = pd.read_csv(PLAYER_FILE, encoding='utf-8-sig')
            df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
            df_lookup['NAVN'] = df_lookup['NAVN'].apply(universal_decode)
            name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
        except: name_map = {}

        df['TAGER_NAVN'] = df.apply(lambda x: name_map.get(str(x['PLAYER_UUID']).strip(), x['PLAYER_NAME']), axis=1)
        
        def find_target(row):
            if row['P1_TEAM'] == row['TEAM_UUID'] and row['P1_UUID'] != row['PLAYER_UUID']:
                return name_map.get(str(row['P1_UUID']).strip(), row['P1_NAME'])
            return None
        
        df['MODTAGER'] = df.apply(find_target, axis=1)
        shot_types = [13, 14, 15, 16]
        df['ER_AFSLUTNING'] = df.apply(lambda x: 1 if x['P1_TYPE'] in shot_types or x['P2_TYPE'] in shot_types or x['P3_TYPE'] in shot_types else 0, axis=1)
        return df
    except Exception as e:
        st.error(f"SQL-fejl: {e}")
        return pd.DataFrame()

def get_summary_stats(df_subset, group_col):
    if df_subset.empty:
        return pd.DataFrame()
    
    total_actions = len(df_subset)
    df_subset = df_subset.copy()
    df_subset['ER_SUCCES'] = df_subset['MODTAGER'].notna().astype(int)
    df_subset['ER_AFSLUTNING'] = pd.to_numeric(df_subset.get('ER_AFSLUTNING', 0), errors='coerce').fillna(0).astype(int)
    
    agg = df_subset.groupby(group_col).agg(
        Antal=(group_col, 'count'),
        Succes_Sum=('ER_SUCCES', 'sum'),
        Afslutning_Sum=('ER_AFSLUTNING', 'sum')
    ).reset_index()
    
    agg['Succes %'] = agg.apply(
        lambda row: int(round((row['Succes_Sum'] / row['Antal']) * 100)) if row['Antal'] > 0 else 0, axis=1
    )
    
    agg['Med afslutning'] = agg['Afslutning_Sum']
    
    agg['Andel'] = agg.apply(
        lambda row: f"{round((row['Antal'] / total_actions) * 100, 1)}%" if total_actions > 0 else "0%", axis=1
    )
    
    agg = agg.sort_values(by='Antal', ascending=False)
    
    if group_col == 'KLUB_NAVN':
        agg = agg[['KLUB_NAVN', 'Antal', 'Succes %', 'Med afslutning', 'Andel']]
        agg.columns = ['Hold', 'Antal', 'Succes %', 'Med afslutning', 'Andel']
    else:
        agg = agg[['TAGER_NAVN', 'Antal', 'Succes %', 'Med afslutning', 'Andel']]
        agg.columns = ['Spiller', 'Antal', 'Succes %', 'Med afslutning', 'Andel']
        
    return agg

def render_setpiece_analysis(df_team, sp_type, t_sel):
    t_info = next((info for name, info in TEAMS.items() if name == t_sel), None)
    hold_logo = get_logo_img(t_info.get('opta_uuid') if t_info else None)

    f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.2, 1])
    with f1:
        p_list = ["Alle spillere"] + sorted(df_team[df_team['TYPE_NAVN'] == sp_type]['TAGER_NAVN'].unique().tolist())
        p_sel = st.selectbox(f"Spiller ({sp_type})", p_list, key=f"sb_p_{sp_type}")
    with f2:
        side_sel = st.selectbox(f"Side ({sp_type})", ["Begge sider", "Venstre side", "Højre side"], key=f"sb_side_{sp_type}")
    with f3:
        kun_afslutning = st.selectbox(f"Filter ({sp_type})", ["Alle", "Kun med afslutning"], key=f"sb_shot_{sp_type}")
    with f4:
        vis_mode = st.selectbox(f"Visning ({sp_type})", ["Zoner + Pile", "Kun Zoner", "Kun Pile"], key=f"sb_m_{sp_type}")

    mask = (df_team['TYPE_NAVN'] == sp_type)
    if p_sel != "Alle spillere": mask &= (df_team['TAGER_NAVN'] == p_sel)
    
    df_plot = df_team[mask].copy()
    df_plot = df_plot[~((df_plot['EVENT_X'] == 0) & (df_plot['EVENT_Y'] == 0))]

    for c in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']: 
        df_plot[c] = pd.to_numeric(df_plot[c], errors='coerce')

    if side_sel == "Venstre side":
        df_plot = df_plot[df_plot['EVENT_Y'] > 50]
    elif side_sel == "Højre side":
        df_plot = df_plot[df_plot['EVENT_Y'] <= 50]

    if kun_afslutning == "Kun med afslutning":
        df_plot = df_plot[df_plot['ER_AFSLUTNING'] == 1]

    total = len(df_plot)
    succes = int(df_plot['MODTAGER'].notna().sum())
    pct = round((succes / total * 100), 0) if total > 0 else 0

    col_p, col_s = st.columns([2.2, 0.8]) 
    
    with col_p:
        t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
        
        if sp_type == "Hjørnespark":
            pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='white', line_color='#333333', linewidth=1.5)
            fig, ax = pitch.draw(figsize=(7, 7))
            if hold_logo:
                # Tilpasset VerticalPitch koordinater i venstre side (nær midterlinjen / bunden)
                ax_logo = ax.inset_axes([3.0, 52.0, 6.0, 6.0], transform=ax.transData)
                ax_logo.imshow(hold_logo)
                ax_logo.axis('off')
                ax.text(11.0, 55.0, t_sel.upper(), fontsize=8, fontweight='bold', color='#222222', va='center')
            
            # Tekst og statistik placeret i venstre side over logoet
            ax.text(36.0, 55.0, f"{sp_type.upper()} ({side_sel.upper()})", fontsize=7, fontweight='bold', color='#555555', va='center')
            spiller_tekst = f"Spiller: {p_sel}" if p_sel != "Alle spillere" else "Alle spillere"
            stats_line = f"{spiller_tekst} — {total} aktioner ({int(pct)}% succes)"
            ax.text(3.0, 65.0, stats_line, fontsize=7, color='#666666', va='center')
        else:
            pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#333333', linewidth=1.5)
            fig, ax = pitch.draw(figsize=(9, 6))
            if hold_logo:
                ax_logo = ax.inset_axes([3.0, 91.0, 6.0, 6.0], transform=ax.transData)
                ax_logo.imshow(hold_logo)
                ax_logo.axis('off')
                ax.text(11.0, 94.0, t_sel.upper(), fontsize=8, fontweight='bold', color='#222222', va='center')
            ax.text(3.0, 87.0, f"{sp_type.upper()} ({side_sel.upper()})", fontsize=7, fontweight='bold', color='#555555', va='center')
            spiller_tekst = f"Spiller: {p_sel}" if p_sel != "Alle spillere" else "Alle spillere"
            stats_line = f"{spiller_tekst} — {total} aktioner ({int(pct)}% succes)"
            ax.text(3.0, 84.0, stats_line, fontsize=7, color='#666666', va='center')

        x = df_plot['EVENT_X']
        y = df_plot['EVENT_Y']
        end_x = df_plot['ENDX']
        end_y = df_plot['ENDY']

        if not df_plot.dropna(subset=['ENDX', 'ENDY']).empty:
            if "Zoner" in vis_mode:
                pitch.hexbin(end_x, end_y, ax=ax, edgecolors='#ffffff', gridsize=(8, 8), cmap='Reds', alpha=0.65)
            if "Pile" in vis_mode:
                pitch.arrows(x, y, end_x, end_y, color=t_color, ax=ax, width=1.5, headwidth=3, headlength=3, alpha=0.5)
                pitch.scatter(x, y, ax=ax, color=t_color, s=25, alpha=0.7)
                
        st.pyplot(fig, clear_figure=True)
        
    with col_s:
        st.write("**Top 5-servere**")
        df_server_base = df_team[df_team['TYPE_NAVN'] == sp_type].copy()
        total_team_actions = len(df_server_base)
        
        df_server_base['ER_SUCCES'] = df_server_base['MODTAGER'].notna().astype(int)
        df_server_base['ER_AFSLUTNING'] = pd.to_numeric(df_server_base.get('ER_AFSLUTNING', 0), errors='coerce').fillna(0).astype(int)
        
        server_agg = df_server_base.groupby('TAGER_NAVN').agg(
            Antal=('TAGER_NAVN', 'count'),
            Succes_Sum=('ER_SUCCES', 'sum'),
            Afslutning_Sum=('ER_AFSLUTNING', 'sum')
        ).reset_index()
        
        server_agg['Succes'] = server_agg.apply(
            lambda row: f"{int(round((row['Succes_Sum'] / row['Antal']) * 100))}%" if row['Antal'] > 0 else "0%", axis=1
        )
        
        server_agg['Andel'] = server_agg.apply(
            lambda row: f"{round((row['Antal'] / total_team_actions) * 100, 1)}%" if total_team_actions > 0 else "0%", axis=1
        )
        
        server_agg = server_agg.sort_values(by='Antal', ascending=False).head(5)
        server_agg = server_agg[['TAGER_NAVN', 'Antal', 'Succes', 'Afslutning_Sum', 'Andel']]
        server_agg.columns = ['Spiller', 'Antal', 'Succes', 'Med afslutning', 'Andel']
        st.dataframe(server_agg, use_container_width=True, hide_index=True)

        st.markdown("---")

        st.write("**Top 5-modtagere**")
        df_mod_base = df_team[(df_team['TYPE_NAVN'] == sp_type) & (df_team['MODTAGER'].notna())].copy()
        total_mod_team = len(df_mod_base)
        
        df_mod_base['ER_AFSLUTNING'] = pd.to_numeric(df_mod_base.get('ER_AFSLUTNING', 0), errors='coerce').fillna(0).astype(int)
        
        mod_agg = df_mod_base.groupby('MODTAGER').agg(
            Antal=('MODTAGER', 'count'),
            Afslutning_Sum=('ER_AFSLUTNING', 'sum')
        ).reset_index()
        
        mod_agg['Andel'] = mod_agg.apply(
            lambda row: f"{round((row['Antal'] / total_mod_team) * 100, 1)}%" if total_mod_team > 0 else "0%", axis=1
        )
        
        mod_agg = mod_agg.sort_values(by='Antal', ascending=False).head(5)
        mod_agg = mod_agg[['MODTAGER', 'Antal', 'Afslutning_Sum', 'Andel']]
        mod_agg.columns = ['Modtager', 'Antal', 'Med afslutning', 'Andel']
        st.dataframe(mod_agg, use_container_width=True, hide_index=True)
        
def vis_side():
    df_all = load_setpiece_data()
    if df_all.empty: st.warning("Ingen data fundet."); return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    c_title, c_drop = st.columns([3, 1])
    with c_title:
        st.subheader("Standardsituationer")
    with c_drop:
        default_idx = teams.index("Hvidovre") if "Hvidovre" in teams else 0
        t_sel = st.selectbox("Vælg hold", teams, index=default_idx, key="main_team_selectbox", label_visibility="collapsed")

    df_team_selected = df_all[df_all['KLUB_NAVN'] == t_sel].copy()
    tabs = st.tabs(["Holdoversigt", "Spilleroversigt", "Hjørnespark", "Frispark", "Indkast", "Zoneoversigt"])
    col_cfg = {"Succes %": st.column_config.ProgressColumn("Succes %", format="%d%%", min_value=0, max_value=100)}

    with tabs[0]: 
        col_content, col_control = st.columns([3, 1])
        with col_control:
            c = st.segmented_control("k1", ["Hjørnespark", "Frispark", "Indkast"], default="Hjørnespark", key="r1", label_visibility="collapsed")
        with col_content:
            st.markdown("### Holdoversigt")
            
        if c:
            st.dataframe(get_summary_stats(df_all[df_all['TYPE_NAVN'] == c], 'KLUB_NAVN'), use_container_width=True, hide_index=True, column_config=col_cfg)

    with tabs[1]: 
        col_content, col_control = st.columns([3, 1])
        with col_control:
            c2 = st.segmented_control("k2", ["Hjørnespark", "Frispark", "Indkast"], default="Hjørnespark", key="r2", label_visibility="collapsed")
        with col_content:
            st.markdown("### Tager-oversigt")
            
        if c2:
            st.dataframe(get_summary_stats(df_team_selected[df_team_selected['TYPE_NAVN'] == c2], 'TAGER_NAVN'), use_container_width=True, hide_index=True, column_config=col_cfg)
    
    for i, name in enumerate(["Hjørnespark", "Frispark", "Indkast"], 2):
        with tabs[i]: 
            render_setpiece_analysis(df_team_selected, name, t_sel)
    
    with tabs[5]:
        st.markdown("### Zoneoversigter & Bane")
        
        pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333333', linewidth=1.5)
        fig, ax = pitch.draw(figsize=(10, 7))
        st.pyplot(fig, clear_figure=True)
        
        df_team_selected['ZONE'] = df_team_selected['ENDY'].apply(lambda y: "Venstre" if float(y or 0) < 33 else ("Højre" if float(y or 0) > 66 else "Center"))
        st.dataframe(df_team_selected.groupby(['ZONE', 'TYPE_NAVN']).size().unstack(fill_value=0), use_container_width=True)

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Standardsituationer")
    st.markdown("<style>header {visibility: hidden;}</style>", unsafe_allow_html=True)
    vis_side()
