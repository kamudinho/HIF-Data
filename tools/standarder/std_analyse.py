import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
# Opdateret LIGA_UUID til 2025/2026 NordicBet Liga hvis nødvendigt
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
PLAYER_FILE = 'data/players/1div_overskrivning.csv'

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: 
        return pd.DataFrame()
    
    # SQL rettet med de præcise navne: EVENT_EVENTID og EVENT_OPTAUUID
    sql = f"""
    WITH BaseEvents AS (
        SELECT 
            e.EVENT_OPTAUUID, 
            e.MATCH_OPTAUUID, 
            e.EVENT_EVENTID,
            e.EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,
            TRIM(e.PLAYER_OPTAUUID) AS PLAYER_UUID,
            e.PLAYER_NAME,
            e.EVENT_X, 
            e.EVENT_Y,
            -- Sekvens-logik baseret på EVENT_EVENTID (Position 12 i din tabel)
            LEAD(TRIM(e.PLAYER_OPTAUUID), 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_UUID,
            LEAD(e.PLAYER_NAME, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_NAME,
            LEAD(e.EVENT_CONTESTANT_OPTAUUID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_TEAM,
            LEAD(TRIM(e.PLAYER_OPTAUUID), 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P2_UUID,
            LEAD(e.PLAYER_NAME, 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P2_NAME,
            LEAD(e.EVENT_CONTESTANT_OPTAUUID, 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P2_TEAM
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
        if df is None or df.empty: 
            return pd.DataFrame()
        df.columns = [c.upper() for c in df.columns]
    except Exception as e:
        st.error(f"Fejl i SQL-hentning: {e}")
        return pd.DataFrame()

    # --- NAVNE MAPPING ---
    try:
        df_lookup = pd.read_csv(PLAYER_FILE)
        df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
        name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
    except:
        name_map = {}

    def format_name(uuid, db_name):
        if pd.isna(uuid) or uuid is None: return None
        u = str(uuid).strip()
        return name_map.get(u, f"{db_name}")

    df['TAGER_NAVN'] = df.apply(lambda x: format_name(x['PLAYER_UUID'], x['PLAYER_NAME']), axis=1)

    # --- MODTAGER LOGIK ---
    def find_target(row):
        # Tjekker om de næste i sekvensen er fra samme hold
        if row['P1_TEAM'] == row['TEAM_UUID'] and row['P1_UUID'] != row['PLAYER_UUID']:
            return format_name(row['P1_UUID'], row['P1_NAME'])
        if row['P2_TEAM'] == row['TEAM_UUID'] and row['P2_UUID'] != row['PLAYER_UUID']:
            return format_name(row['P2_UUID'], row['P2_NAME'])
        return None

    df['MODTAGER'] = df.apply(find_target, axis=1)
    
    for col in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return df

def to_metric(val, total_m): 
    return val * (total_m / 100)

def vis_side():
    st.set_page_config(layout="wide")
    # Skjul Streamlit standard menu
    st.markdown("<style>header {visibility: hidden;}</style>", unsafe_allow_html=True)
    
    st.title("Standard-Analyse")
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet. Tjek din LIGA_UUID og Snowflake-forbindelse.")
        return

    # Klub mapping fra team_mapping.py
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])
    
    # --- FILTRE (4 kolonner i toppen) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        t_sel = st.selectbox("Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    with c2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with c3:
        players = ["Alle spillere"] + sorted(df_team[df_team['TYPE_NAVN'] == sp_type]['TAGER_NAVN'].unique().tolist())
        p_sel = st.selectbox("Spiller", players)
    with c4:
        vis_mode = st.selectbox("Visning", ["Zoner + Pile", "Kun Zoner", "Kun Pile"])

    # Filtrering af plot-data
    mask = (df_team['TYPE_NAVN'] == sp_type)
    if p_sel != "Alle spillere":
        mask &= (df_team['TAGER_NAVN'] == p_sel)
    
    df_plot = df_team[mask].copy()

    # Metrisk skalering (Opta er 0-100, Pitch er 105x68)
    df_plot['X_M'] = df_plot['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_plot['Y_M'] = df_plot['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_plot['ENDX_M'] = df_plot['ENDX'].apply(lambda x: to_metric(x, 105))
    df_plot['ENDY_M'] = df_plot['ENDY'].apply(lambda y: to_metric(y, 68))

    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
    
    # --- VISUALISERING ---
    col_p, col_s = st.columns([2, 1])

    with col_p:
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 12))
        ax.set_ylim(50, 105) # Vis kun modstanderens banehalvdel

        if not df_plot.dropna(subset=['ENDX_M', 'ENDY_M']).empty:
            if "Zoner" in vis_mode:
                pitch.hexbin(df_plot.ENDX_M, df_plot.ENDY_M, ax=ax, gridsize=(12, 12), cmap='Reds', alpha=0.6, edgecolors='#f0f0f0')
            if "Pile" in vis_mode:
                alpha_val = 0.4 if len(df_plot) < 100 else 0.15
                pitch.arrows(df_plot.X_M, df_plot.Y_M, df_plot.ENDX_M, df_plot.ENDY_M, 
                             width=1, headwidth=3, color=t_color, ax=ax, alpha=alpha_val)
        st.pyplot(fig)

    with col_s:
        st.subheader("Statistik")
        st.metric("Antal aktioner", len(df_plot))
        
        def get_top_receiver(group):
            m_counts = group['MODTAGER'].value_counts()
            if not m_counts.empty:
                return f"{m_counts.idxmax()} ({m_counts.max()})"
            return "Ingen"

        st.write("**Top eksekutører:**")
        st.dataframe(df_plot['TAGER_NAVN'].value_counts(), use_container_width=True)
        
        st.write("**Primære modtagere (Mønster):**")
        if not df_plot.empty:
            receiver_df = df_plot.groupby('TAGER_NAVN').apply(lambda x: pd.Series({
                'Primær Modtager': get_top_receiver(x),
                'Ramte / Duel': x['MODTAGER'].notna().sum()
            }), include_groups=False).reset_index()
            st.dataframe(receiver_df.sort_values('Ramte / Duel', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Ingen data for valgte filter.")

if __name__ == "__main__":
    vis_side()
