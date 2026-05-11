import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn
from PIL import Image
import requests
from io import BytesIO

# --- KONFIGURATION ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    
    # Vi henter events og bruger Qualifiers til at identificere Set Pieces
    # QID 2 = Corner, QID 5 = Free kick, QID 107 = Throw-in
    sql = f"""
        SELECT 
            e.EVENT_OPTAUUID, e.EVENT_X, e.EVENT_Y, e.EVENT_ENDX, e.EVENT_ENDY, 
            e.EVENT_TYPEID, e.EVENT_CONTESTANT_OPTAUUID, e.PLAYER_OPTAUUID,
            q.QUALIFIER_QID,
            TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        LEFT JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE q.QUALIFIER_QID IN (2, 5, 107, 124) -- Corner, Free Kick, Throw-in, Corner Taken
        AND e.MATCH_OPTAUUID IN ({match_sql})
    """
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]
    
    # Map Qualifier til tekst
    type_map = {2: "Hjørnespark", 124: "Hjørnespark", 5: "Frispark", 107: "Indkast"}
    df['SET_PIECE_TYPE'] = df['QUALIFIER_QID'].map(type_map)
    
    return df

@st.cache_data(ttl=3600)
def get_logo_img(url):
    try: return Image.open(BytesIO(requests.get(url, timeout=5).content))
    except: return None

def to_metric(val, total_m):
    return val * (total_m / 100)

# --- MAIN APP ---
def vis_side():
    st.markdown("<style>header {visibility: hidden;} .main .block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)

    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet for standardsituationer.")
        return

    # Team Mapping
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    # Topbar
    c_h1, c_h2, c_h3 = st.columns([1, 1, 1])
    with c_h1:
        t_sel = st.selectbox("Hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    with c_h2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with c_h3:
        side_sel = st.selectbox("Side", ["Begge", "Venstre", "Højre"])

    # Filtrering
    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()
    
    # Skalér til meter
    df_team['X_M'] = df_team['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_team['Y_M'] = df_team['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_team['ENDX_M'] = df_team['EVENT_ENDX'].apply(lambda x: to_metric(x, 105))
    df_team['ENDY_M'] = df_team['EVENT_ENDY'].apply(lambda y: to_metric(y, 68))

    # Filtrer på side (baseret på Y-koordinat, da vi ser banen vertikalt)
    if side_sel == "Venstre":
        df_team = df_team[df_team['Y_M'] < 34]
    elif side_sel == "Højre":
        df_team = df_team[df_team['Y_M'] >= 34]

    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
    
    # Layout
    col_plot, col_stats = st.columns([2, 1])

    with col_plot:
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 12))
        ax.set_ylim(50, 105) # Fokus på den angribende halvdel

        if not df_team.empty:
            # Tegn pile for hver aktion
            pitch.arrows(df_team.X_M, df_team.Y_M, df_team.ENDX_M, df_team.ENDY_M, 
                         width=2, headwidth=3, headlength=3, color=t_color, ax=ax, alpha=0.4, label=sp_type)
            
            # Marker slutpunkterne
            pitch.scatter(df_team.ENDX_M, df_team.ENDY_M, s=60, edgecolors=t_color, c='white', linewidth=1, alpha=0.6, ax=ax)

        st.pyplot(fig)

    with col_stats:
        st.subheader("Analyse")
        total = len(df_team)
        st.metric(f"Total {sp_type}", total)

        if total > 0:
            # Beregn gennemsnitlig længde
            dist = np.sqrt((df_team.ENDX_M - df_team.X_M)**2 + (df_team.ENDY_M - df_team.Y_M)**2)
            st.write(f"**Gns. længde:** {dist.mean():.1f}m")

            # Top eksekutører
            st.write("**Top eksekutører:**")
            p_counts = df_team['PLAYER_NAME'].value_counts().head(5)
            st.dataframe(p_counts, use_container_width=True)

            # Zone-analyse (Ender den i feltet?)
            in_box = df_team[(df_team.ENDX_M >= 88.5) & (df_team.ENDY_M >= 13.84) & (df_team.ENDY_M <= 54.16)]
            box_pct = (len(in_box) / total) * 100
            st.write(f"**Rammer feltet:** {box_pct:.1f}%")
            
            # Tendens
            fremad = len(df_team[df_team.ENDX_M > df_team.X_M])
            st.write(f"**Søger fremad:** {(fremad/total*100):.1f}%")

if __name__ == "__main__":
    vis_side()
