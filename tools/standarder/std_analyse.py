import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
from PIL import Image
from io import BytesIO
from mplsoccer import Pitch
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. KONFIGURATION ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
PLAYER_FILE = 'data/players/1div_overskrivning.csv'

# --- 2. HJÆLPEFUNKTIONER (LOGO & DECODE) ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    """Henter klublogo fra din TEAMS mapping eller via URL"""
    if not opta_uuid: return None
    url = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def universal_decode(text):
    """Fikser ødelagte tegn fra Norden, Baltikum og Sydeuropa."""
    if not isinstance(text, str): return text
    try: return text.encode('latin1').decode('utf-8')
    except: return text

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
    except: return pd.DataFrame()

# --- 4. STATISTIK BEREGNING ---
def get_summary_stats(df, group_col):
    if df.empty: return pd.DataFrame()
    stats = df.groupby(group_col).agg(
        Antal=('TYPE_NAVN', 'size'),
        Succesfulde=('MODTAGER', lambda x: x.notna().sum()),
        Afslutninger=('ER_AFSLUTNING', 'sum')
    ).reset_index()
    stats['Succes %'] = (stats['Succesfulde'] / stats['Antal'] * 100).round(0).fillna(0)
    stats['Afslutning %'] = (stats['Afslutninger'] / stats['Antal'] * 100).round(0).fillna(0)
    
    def get_top_mod(sub_df):
        m = sub_df['MODTAGER'].value_counts()
        return f"{m.index[0]} ({m.iloc[0]})" if not m.empty else "-"
    
    mod_map = df.groupby(group_col).apply(get_top_mod).to_dict()
    stats['Top Modtager'] = stats[group_col].map(mod_map)
    return stats[[group_col, 'Antal', 'Succes %', 'Top Modtager', 'Afslutning %']]

# --- 5. VISUALISERING (BANE) ---
def render_setpiece_analysis(df_team, sp_type, t_sel):
    t_info = next((info for name, info in TEAMS.items() if name == t_sel), None)
    t_uuid = t_info.get('opta_uuid') if t_info else None
    hold_logo = get_logo_img(t_uuid)

    f1, f2 = st.columns([1, 1])
    with f1:
        p_list = ["Alle spillere"] + sorted(df_team[df_team['TYPE_NAVN'] == sp_type]['TAGER_NAVN'].unique().tolist())
        p_sel = st.selectbox(f"Spiller ({sp_type})", p_list, key=f"sb_p_{sp_type}")
    with f2:
        vis_mode = st.selectbox(f"Visning ({sp_type})", ["Zoner + Pile", "Kun Zoner", "Kun Pile"], key=f"sb_m_{sp_type}")

    mask = (df_team['TYPE_NAVN'] == sp_type)
    if p_sel != "Alle spillere": mask &= (df_team['TAGER_NAVN'] == p_sel)
    df_plot = df_team[mask].copy()
    df_plot = df_plot[~((df_plot['EVENT_X'] == 0) & (df_plot['EVENT_Y'] == 0))]

    total = len(df_plot)
    succes = int(df_plot['MODTAGER'].notna().sum())
    pct = round((succes / total * 100), 0) if total > 0 else 0

    col_p, col_s = st.columns([2, 1]) 
    
    with col_p:
        for c in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']: 
            df_plot[c] = pd.to_numeric(df_plot[c], errors='coerce')

        mask_left = df_plot['EVENT_X'] < 50
        df_plot.loc[mask_left, ['EVENT_X', 'ENDX']] = 100 - df_plot.loc[mask_left, ['EVENT_X', 'ENDX']]
        df_plot.loc[mask_left, ['EVENT_Y', 'ENDY']] = 100 - df_plot.loc[mask_left, ['EVENT_Y', 'ENDY']]

        df_plot['x'], df_plot['y'] = df_plot['EVENT_X'] * 1.05, df_plot['EVENT_Y'] * 0.68
        df_plot['end_x'], df_plot['end_y'] = df_plot['ENDX'] * 1.05, df_plot['ENDY'] * 0.68

        pitch = Pitch(pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#333333', goal_type='box', linewidth=0.6)
        fig, ax = pitch.draw(figsize=(6, 4), constrained_layout=True)
        
        # --- TEKST PÅ BANEN ---
        ax.text(2, 66, sp_type.upper(), fontsize=10, fontweight='bold', color='#333333', alpha=0.8)
        stats_line = f"{p_sel} | {total} aktioner ({int(pct)}% succes)"
        ax.text(2, 62, stats_line, fontsize=8.5, color='#555555', va='top')

        # Logo & Navn
        if hold_logo:
            ax_logo = ax.inset_axes([0.02, 0.04, 0.08, 0.08], transform=ax.transAxes)
            ax_logo.imshow(hold_logo); ax_logo.axis('off')
            ax.text(12, 4, t_sel.upper(), fontsize=9, fontweight='bold', color='#333333', alpha=0.6, va='center')
        else:
            ax.text(2, 4, t_sel.upper(), fontsize=9, fontweight='bold', color='#333333', alpha=0.6, va='center')

        if not df_plot.dropna(subset=['end_x', 'end_y']).empty:
            if "Zoner" in vis_mode:
                pitch.hexbin(df_plot.end_x, df_plot.end_y, ax=ax, edgecolors='#f0f0f0', gridsize=(10, 10), cmap='Reds', alpha=0.7)
            if "Pile" in vis_mode:
                p_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
                pitch.arrows(df_plot.x, df_plot.y, df_plot.end_x, df_plot.end_y, color=p_color, ax=ax, width=0.4, headwidth=2, headlength=2, alpha=0.4)
                pitch.scatter(df_plot.x, df_plot.y, ax=ax, color=p_color, s=12, alpha=0.6)

        st.pyplot(fig)
        
    with col_s:
        st.write("**Top 5-modtagere**")
        mod_counts = df_plot['MODTAGER'].value_counts().reset_index()
        mod_counts.columns = ['Spiller', 'Antal']
        st.dataframe(mod_counts.head(5), use_container_width=True, hide_index=True)

# --- 6. HOVEDSIDE ---
def vis_side():
    st.set_page_config(layout="wide", page_title="Standardsituationer")
    st.markdown("<style>header {visibility: hidden;} div[data-testid='stSelectbox'] label { display: none !important; }</style>", unsafe_allow_html=True)
    
    df_all = load_setpiece_data()
    if df_all.empty: st.warning("Ingen data fundet."); return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    col_t, _, col_sel = st.columns([2, 1, 1])
    with col_t: st.subheader("Standardsituationer")
    with col_sel: t_sel = st.selectbox("h", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)

    df_team_selected = df_all[df_all['KLUB_NAVN'] == t_sel].copy()
    tabs = st.tabs(["Holdoversigt", "Spilleroversigt", "Hjørnespark", "Frispark", "Indkast", "Zoneoversigt"])
    col_cfg = {"Succes %": st.column_config.ProgressColumn("Succes %", format="%d%%", min_value=0, max_value=100)}

    with tabs[0]: 
        c = st.radio("k1", ["Hjørnespark", "Frispark", "Indkast"], horizontal=True, key="r1")
        st.dataframe(get_summary_stats(df_all[df_all['TYPE_NAVN'] == c], 'KLUB_NAVN'), use_container_width=True, hide_index=True, column_config=col_cfg)
    with tabs[1]: 
        c2 = st.radio("k2", ["Hjørnespark", "Frispark", "Indkast"], horizontal=True, key="r2")
        st.dataframe(get_summary_stats(df_team_selected[df_team_selected['TYPE_NAVN'] == c2], 'TAGER_NAVN'), use_container_width=True, hide_index=True, column_config=col_cfg)
    for i, name in enumerate(["Hjørnespark", "Frispark", "Indkast"], 2):
        with tabs[i]: render_setpiece_analysis(df_team_selected, name, t_sel)
    with tabs[5]:
        df_team_selected['ZONE'] = df_team_selected['ENDY'].apply(lambda y: "Venstre" if float(y or 0) < 33 else ("Højre" if float(y or 0) > 66 else "Center"))
        st.dataframe(df_team_selected.groupby(['ZONE', 'TYPE_NAVN']).size().unstack(fill_value=0), use_container_width=True)

if __name__ == "__main__":
    vis_side()
