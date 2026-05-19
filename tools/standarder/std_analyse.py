import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. KONFIGURATION ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
PLAYER_FILE = 'data/players/1div_overskrivning.csv'

# --- 2. HJÆLPEFUNKTIONER (ENCODING & KONVERTERING) ---
def universal_decode(text):
    """Fikser ødelagte tegn fra Norden, Baltikum og Sydeuropa."""
    if not isinstance(text, str):
        return text
    try:
        # Tvinger teksten gennem en latin1-til-utf8 vask
        return text.encode('latin1').decode('utf-8')
    except:
        return text

def to_metric(val, total_m): 
    return val * (total_m / 100)

# --- 3. DATA LOAD ---
@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    sql = f"""
    WITH BaseEvents AS (
        SELECT 
            e.EVENT_OPTAUUID, e.MATCH_OPTAUUID, e.EVENT_EVENTID,
            e.EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,
            e.EVENT_TYPEID,
            TRIM(e.PLAYER_OPTAUUID) AS PLAYER_UUID,
            e.PLAYER_NAME,
            e.EVENT_X, e.EVENT_Y,
            LEAD(TRIM(e.PLAYER_OPTAUUID), 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_UUID,
            LEAD(e.PLAYER_NAME, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_NAME,
            LEAD(e.EVENT_CONTESTANT_OPTAUUID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_TEAM,
            LEAD(e.EVENT_TYPEID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_TYPE,
            LEAD(e.EVENT_TYPEID, 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P2_TYPE,
            LEAD(e.EVENT_TYPEID, 3) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P3_TYPE
        FROM {DB}.OPTA_EVENTS e
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    ),
    Quals AS (
        SELECT 
            EVENT_OPTAUUID,
            MAX(CASE WHEN QUALIFIER_QID = 107 THEN 'Indkast'
                     WHEN QUALIFIER_QID = 6 THEN 'Hjørnespark'
                     WHEN QUALIFIER_QID = 5 THEN 'Frispark' END) AS TYPE_NAVN,
            MAX(CASE WHEN QUALIFIER_QID = 140 THEN QUALIFIER_VALUE END) AS ENDX,
            MAX(CASE WHEN QUALIFIER_QID = 141 THEN QUALIFIER_VALUE END) AS ENDY
        FROM {DB}.OPTA_QUALIFIERS
        WHERE QUALIFIER_QID IN (5, 6, 107, 140, 141)
        GROUP BY EVENT_OPTAUUID
    )
    SELECT b.*, q.TYPE_NAVN, q.ENDX, q.ENDY
    FROM BaseEvents b
    JOIN Quals q ON b.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    WHERE q.TYPE_NAVN IS NOT NULL
    """
    try:
        df = conn.query(sql)
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [c.upper() for c in df.columns]
        
        # Vask navne fra databasen
        df['PLAYER_NAME'] = df['PLAYER_NAME'].apply(universal_decode)
        df['P1_NAME'] = df['P1_NAME'].apply(universal_decode)
        
        try:
            # Læs og vask navne fra lookup-filen
            df_lookup = pd.read_csv(PLAYER_FILE, encoding='utf-8-sig')
            df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
            df_lookup['NAVN'] = df_lookup['NAVN'].apply(universal_decode)
            name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
        except:
            name_map = {}

        df['TAGER_NAVN'] = df.apply(lambda x: name_map.get(str(x['PLAYER_UUID']).strip(), x['PLAYER_NAME']), axis=1)
        
        def find_target(row):
            if row['P1_TEAM'] == row['TEAM_UUID'] and row['P1_UUID'] != row['PLAYER_UUID']:
                target_name = name_map.get(str(row['P1_UUID']).strip(), row['P1_NAME'])
                return target_name
            return None
        
        df['MODTAGER'] = df.apply(find_target, axis=1)

        shot_types = [13, 14, 15, 16]
        df['ER_AFSLUTNING'] = df.apply(lambda x: 1 if x['P1_TYPE'] in shot_types or x['P2_TYPE'] in shot_types or x['P3_TYPE'] in shot_types else 0, axis=1)
        
        return df
    except:
        return pd.DataFrame()

# --- 4. STATISTIK BEREGNING ---
def get_summary_stats(df, group_col):
    if df.empty: return pd.DataFrame()
    
    stats = df.groupby(group_col).agg(
        Antal=('TYPE_NAVN', 'size'),
        Succesfulde=('MODTAGER', lambda x: x.notna().sum()),
        Afslutninger=('ER_AFSLUTNING', 'sum')
    ).reset_index()
    
    # Procent-fix til ProgressColumn (0-100 skala)
    stats['Succes %'] = (stats['Succesfulde'] / stats['Antal'] * 100).round(0).fillna(0)
    stats['Afslutning %'] = (stats['Afslutninger'] / stats['Antal'] * 100).round(0).fillna(0)
    
    def get_top_mod(sub_df):
        m = sub_df['MODTAGER'].value_counts()
        return f"{m.index[0]} ({m.iloc[0]})" if not m.empty else "-"
    
    def get_top_mod_shot(sub_df):
        m = sub_df[sub_df['ER_AFSLUTNING'] == 1]['MODTAGER'].value_counts()
        return f"{m.index[0]} ({m.iloc[0]})" if not m.empty else "-"

    mod_map = df.groupby(group_col).apply(get_top_mod).to_dict()
    mod_shot_map = df.groupby(group_col).apply(get_top_mod_shot).to_dict()
    
    stats['Top Modtager'] = stats[group_col].map(mod_map)
    stats['Top Modtager (Afsl.)'] = stats[group_col].map(mod_shot_map)
    
    final_cols = [group_col, 'Antal', 'Succesfulde', 'Succes %', 'Top Modtager', 'Afslutninger', 'Afslutning %', 'Top Modtager (Afsl.)']
    return stats[final_cols]

# --- 5. VISUALISERING (BANE) ---
def render_setpiece_analysis(df_team, sp_type, t_sel):
    f1, f2 = st.columns([1, 1])
    with f1:
        p_list = ["Alle spillere"] + sorted(df_team[df_team['TYPE_NAVN'] == sp_type]['TAGER_NAVN'].unique().tolist())
        p_sel = st.selectbox(f"Spiller ({sp_type})", p_list, key=f"sb_p_{sp_type}")
    with f2:
        vis_mode = st.selectbox(f"Visning ({sp_type})", ["Zoner + Pile", "Kun Zoner", "Kun Pile"], key=f"sb_m_{sp_type}")

    mask = (df_team['TYPE_NAVN'] == sp_type)
    if p_sel != "Alle spillere": mask &= (df_team['TAGER_NAVN'] == p_sel)
    df_plot = df_team[mask].copy()

    # Fejlsikring mod 0,0 data
    df_plot = df_plot[~((df_plot['EVENT_X'] == 0) & (df_plot['EVENT_Y'] == 0))]
    df_plot = df_plot[~((df_plot['ENDX'] == 0) & (df_plot['ENDY'] == 0))]

    from mplsoccer import Pitch 

    col_p, col_s = st.columns([2.5, 1])
    with col_p:
        for c in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']: 
            df_plot[c] = pd.to_numeric(df_plot[c], errors='coerce')

        # Normalisering til højre (x=100)
        mask_left = df_plot['EVENT_X'] < 50
        df_plot.loc[mask_left, ['EVENT_X', 'ENDX']] = 100 - df_plot.loc[mask_left, ['EVENT_X', 'ENDX']]
        df_plot.loc[mask_left, ['EVENT_Y', 'ENDY']] = 100 - df_plot.loc[mask_left, ['EVENT_Y', 'ENDY']]

        # Konverter til meter (105x68)
        df_plot['x'] = df_plot['EVENT_X'] * 1.05
        df_plot['y'] = df_plot['EVENT_Y'] * 0.68
        df_plot['end_x'] = df_plot['ENDX'] * 1.05
        df_plot['end_y'] = df_plot['ENDY'] * 0.68

        # Pitch konfiguration
        pitch = Pitch(pitch_type='custom', pitch_length=105, pitch_width=68, 
                      line_color='#333333', goal_type='box', linewidth=1)
        
        # Vi fjerner faste grænser for at lade Pitch styre proportionerne (ingen zoom)
        fig, ax = pitch.draw(figsize=(12, 8))
        
        # VIGTIGT: Vi sætter grænserne til banens faktiske mål (105x68)
        # Det fjerner tomrummet der skubber banen ned
        ax.set_xlim(0, 105)
        ax.set_ylim(0, 68) 

        if not df_plot.dropna(subset=['end_x', 'end_y']).empty:
            if "Zoner" in vis_mode:
                pitch.hexbin(df_plot.end_x, df_plot.end_y, ax=ax, edgecolors='#f0f0f0',
                             gridsize=(15, 15), cmap='Reds', alpha=0.7)
            
            if "Pile" in vis_mode:
                p_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
                pitch.arrows(df_plot.x, df_plot.y, df_plot.end_x, df_plot.end_y, 
                             color=p_color, ax=ax, width=1.2, headwidth=3, headlength=3, alpha=0.3)
                
                pitch.scatter(df_plot.x, df_plot.y, ax=ax, color=p_color, s=15, alpha=0.5)

        st.pyplot(fig)
        
    with col_s:
        m1, m2, m3 = st.columns(3)
        m1.metric("Antal", len(df_plot))
        m2.metric("Succes", df_plot['MODTAGER'].notna().sum())
        m3.metric("Afslutn.", df_plot['ER_AFSLUTNING'].sum())
        st.write("---") 
        st.write("**Top modtagere**")
        mod_counts = df_plot['MODTAGER'].value_counts().reset_index()
        mod_counts.columns = ['Spiller', 'Antal']
        st.dataframe(mod_counts, use_container_width=True, hide_index=True)
        
# --- 6. HOVEDSIDE ---
def vis_side():
    st.set_page_config(layout="wide", page_title="Standardsituationer")
    
    st.markdown("""
        <style>
        header {visibility: hidden;}
        div[data-testid="stSelectbox"] label { display: none !important; }
        div[data-testid="stHorizontalBlock"] { align-items: center; }
        </style>
    """, unsafe_allow_html=True)
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet.")
        return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    col_title, col_empty, col_select = st.columns([2, 1, 1])
    with col_title:
        st.subheader("Standardsituationer")
    with col_select:
        t_sel = st.selectbox("hold_valg_top", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)

    df_team_selected = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    tabs = st.tabs(["Holdoversigt", "Spilleroversigt", "Hjørnespark", "Frispark", "Indkast", "Zoneoversigt"])
    cat_options = ["Hjørnespark", "Frispark", "Indkast"]

    # Konfiguration af kolonner med korrekt procent-visning
    col_cfg = {
        "KLUB_NAVN": "Klub",
        "TAGER_NAVN": "Spiller",
        "Succes %": st.column_config.ProgressColumn("Succes %", format="%d%%", min_value=0, max_value=100),
        "Top Modtager": "Modtager (Succes)",
        "Afslutning %": st.column_config.ProgressColumn("Afslutning %", format="%d%%", min_value=0, max_value=100),
        "Top Modtager (Afsl.)": "Modtager (Afsl.)"
    }

    with tabs[0]: 
        c_label, c_radio = st.columns([0.15, 0.85])
        with c_label: st.write("**Kategori**")
        with c_radio: cat_h = st.radio("cat_h", cat_options, horizontal=True, label_visibility="collapsed", key="radio_hold")
        stats_h = get_summary_stats(df_all[df_all['TYPE_NAVN'] == cat_h], 'KLUB_NAVN')
        st.dataframe(stats_h, use_container_width=True, hide_index=True, height=500, column_config=col_cfg)

    with tabs[1]: 
        c_label_s, c_radio_s = st.columns([0.15, 0.85])
        with c_label_s: st.write("**Kategori**")
        with c_radio_s: cat_s = st.radio("cat_s", cat_options, horizontal=True, label_visibility="collapsed", key="radio_spiller")
        df_cat_s = df_team_selected[df_team_selected['TYPE_NAVN'] == cat_s]
        if not df_cat_s.empty:
            stats_s = get_summary_stats(df_cat_s, 'TAGER_NAVN')
            st.dataframe(stats_s, use_container_width=True, hide_index=True, height=500, column_config=col_cfg)

    with tabs[2]: render_setpiece_analysis(df_team_selected, "Hjørnespark", t_sel)
    with tabs[3]: render_setpiece_analysis(df_team_selected, "Frispark", t_sel)
    with tabs[4]: render_setpiece_analysis(df_team_selected, "Indkast", t_sel)

    with tabs[5]:
        df_team_selected['ZONE'] = df_team_selected['ENDY'].apply(lambda y: "Venstre" if float(y or 0) < 33 else ("Højre" if float(y or 0) > 66 else "Center"))
        zone_stats = df_team_selected.groupby(['ZONE', 'TYPE_NAVN']).size().unstack(fill_value=0).reset_index()
        st.dataframe(zone_stats, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    vis_side()
