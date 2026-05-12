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
    if not conn: 
        return pd.DataFrame()

    # Sub-query til at finde kampe i den valgte sæson
    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"

    # SQL der henter hændelser og deres slut-koordinater (QID 140/141)
    sql = f"""
    WITH END_X AS (
        SELECT EVENT_OPTAUUID, QUALIFIER_VALUE as ENDX FROM {DB}.OPTA_QUALIFIERS WHERE QUALIFIER_QID = 140
    ),
    END_Y AS (
        SELECT EVENT_OPTAUUID, QUALIFIER_VALUE as ENDY FROM {DB}.OPTA_QUALIFIERS WHERE QUALIFIER_QID = 141
    ),
    SET_PIECE_EVENTS AS (
        SELECT e.EVENT_OPTAUUID, e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
               e.EVENT_CONTESTANT_OPTAUUID, e.PLAYER_OPTAUUID, q.QUALIFIER_QID, e.MATCH_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE q.QUALIFIER_QID IN (2, 5, 107, 124) -- Corner, Free Kick, Throw-in
        AND e.MATCH_OPTAUUID IN ({match_sql})
    )
    SELECT 
        s.*,
        ex.ENDX as EVENT_ENDX,
        ey.ENDY as EVENT_ENDY,
        TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as PLAYER_NAME
    FROM SET_PIECE_EVENTS s
    LEFT JOIN END_X ex ON s.EVENT_OPTAUUID = ex.EVENT_OPTAUUID
    LEFT JOIN END_Y ey ON s.EVENT_OPTAUUID = ey.EVENT_OPTAUUID
    LEFT JOIN {DB}.OPTA_PLAYERS p ON s.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
    """
    
    df = conn.query(sql)
    df.columns = [c.upper() for c in df.columns]

    # Konverter koordinater til tal
    for col in ['EVENT_X', 'EVENT_Y', 'EVENT_ENDX', 'EVENT_ENDY']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Mapping af typer baseret på Opta Qualifiers
    type_map = {2: "Hjørnespark", 124: "Hjørnespark", 5: "Frispark", 107: "Indkast"}
    df['SET_PIECE_TYPE'] = df['QUALIFIER_QID'].map(type_map)

    return df

def to_metric(val, total_m):
    return val * (total_m / 100)

# --- MAIN APP ---
def vis_side():
    st.markdown("<style>header {visibility: hidden;} .main .block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)

    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet. Tjek om ligaens UUID og Snowflake-forbindelsen er korrekt.")
        return

    # Team Mapping fra din utils
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    
    # Hent liste over hold til dropdown
    teams_in_data = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    # Filtre i toppen
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        t_sel = st.selectbox("Hold", teams_in_data, index=teams_in_data.index("Hvidovre") if "Hvidovre" in teams_in_data else 0)
    with col_f2:
        sp_type = st.selectbox("Type", ["Hjørnespark", "Indkast", "Frispark"])
    with col_f3:
        side_sel = st.selectbox("Side", ["Begge", "Venstre", "Højre"])

    # Filtrering af data baseret på valg
    df_team = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['SET_PIECE_TYPE'] == sp_type)].copy()

    # Skalering til banens mål (meter)
    df_team['X_M'] = df_team['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_team['Y_M'] = df_team['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_team['ENDX_M'] = df_team['EVENT_ENDX'].apply(lambda x: to_metric(x, 105))
    df_team['ENDY_M'] = df_team['EVENT_ENDY'].apply(lambda y: to_metric(y, 68))

    # Filtrering på side (Venstre/Højre)
    if side_sel == "Venstre":
        df_team = df_team[df_team['Y_M'] < 34]
    elif side_sel == "Højre":
        df_team = df_team[df_team['Y_M'] >= 34]

    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)

    # Layout med bane og statistik
    col_p, col_s = st.columns([2, 1])
    
    with col_p:
        # Vi viser kun den øverste halvdel af banen (half=True)
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 12))
        ax.set_ylim(50, 105) # Zoom ind på modstanderens banehalvdel

        if not df_team.dropna(subset=['ENDX_M', 'ENDY_M']).empty:
            # Tegn pile for bevægelse
            pitch.arrows(df_team.X_M, df_team.Y_M, df_team.ENDX_M, df_team.ENDY_M, 
                         width=2, headwidth=4, headlength=4, color=t_color, ax=ax, alpha=0.5)

            # Scatter slutpunkter (hvor bolden lander)
            pitch.scatter(df_team.ENDX_M, df_team.ENDY_M, s=80, edgecolors='black', 
                          c=t_color, linewidth=1, alpha=0.8, ax=ax, zorder=3)
        else:
            st.info("Ingen slut-koordinater tilgængelige for dette valg.")
        
        st.pyplot(fig)

    with col_s:
        st.subheader("Statistik")
        total = len(df_team)
        st.metric("Antal aktioner", total)
        
        if total > 0:
            st.write("**Top udførere:**")
            st.dataframe(df_team['PLAYER_NAME'].value_counts().head(5), use_container_width=True)

            # Beregn hvor mange der rammer "feltet" (zone-estimat)
            in_box = df_team[(df_team.ENDX_M >= 88.5) & (df_team.ENDY_M >= 13.8) & (df_team.ENDY_M <= 54.2)]
            box_pct = (len(in_box) / total) * 100 if total > 0 else 0
            st.metric("Rammer feltet (%)", f"{box_pct:.1f}%")
            
            # Beregn tendens (aktioner der flytter bolden mindst 5 meter fremad)
            fremad = len(df_team[df_team.ENDX_M > df_team.X_M + 5])
            fremad_pct = (fremad / total) * 100 if total > 0 else 0
            st.write(f"**Søger fremad/feltet:** {int(fremad_pct)}%")

if __name__ == "__main__":
    vis_side()
