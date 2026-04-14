import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from mplsoccer import Pitch
import matplotlib.pyplot as plt
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
# Superliga (335) er fjernet herfra for at sikre, at vi kun ser dine relevante ligaer
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '328', '329', '43319', '331')"
CURRENT_SEASON = "2025/2026"

@st.cache_data(ttl=600)
def get_detailed_run_data(player_name, player_opta_uuid, valgt_hold_navn, _conn):
    """Henter de enkelte løbe-aktioner med koordinater til pil-visning"""
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    # SQL forespørgsel til tabellen med de enkelte løbe-events (Second Spectrum)
    sql = f"""
        SELECT 
            START_X, START_Y, END_X, END_Y, PHASE, SPEED_CATEGORY, MATCH_DATE
        FROM {DB}.SECONDSPECTRUM_RUN_EVENTS
        WHERE (({name_conditions}) OR ("optaId" LIKE '%{clean_id}%'))
          AND MATCH_DATE >= '2025-07-01'
          AND SPEED_CATEGORY IN ('HSR', 'SPRINT')
          AND MATCH_SSIID IN (
              SELECT MATCH_SSIID FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' OR AWAY_SSIID = '{target_ssiid}'
          )
    """
    return _conn.query(sql)

def draw_run_pitch(df_runs, phase, color, title):
    """Tegner banen med pile (Vektorer) for hvert løb"""
    # Opta-banetype (0-100) matcher ofte Second Spectrum eksporten bedst
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD', line_zorder=2)
    fig, ax = pitch.draw(figsize=(10, 8))
    fig.set_facecolor('none')
    
    # Filtrer på fase
    phase_data = df_runs[df_runs['PHASE'] == phase].copy()
    
    if not phase_data.empty:
        # Vi tegner pile fra start (x,y) til slut (end_x, end_y)
        pitch.arrows(phase_data.START_X, phase_data.START_Y, 
                     phase_data.END_X, phase_data.END_Y, 
                     width=2, headwidth=4, headlength=4, 
                     color=color, ax=ax, alpha=0.7)
        
        # Tilføj små prikker ved startpositionen for tydelighed
        pitch.scatter(phase_data.START_X, phase_data.START_Y, 
                      s=20, color=color, edgecolors='white', linewidth=0.5, alpha=0.8, ax=ax)
    else:
        ax.text(50, 50, "Ingen registrerede løb i denne fase", 
                ha='center', va='center', alpha=0.5, fontsize=12)

    ax.set_title(title, fontsize=16, pad=15, fontweight='bold', color='#333333')
    return fig

def vis_side():
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 22px !important; font-weight: bold !important; color: #cc0000; }
        .stTabs [aria-selected="true"] { background-color: #cc0000 !important; color: white !important; font-weight: bold; }
        .main-title { font-size: 28px; font-weight: bold; color: #1E1E1E; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- FILTRERING AF HOLD (KUN DINE LIGAER) ---
    sql_teams = f"""
        SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID 
        FROM {DB}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}
    """
    df_teams_raw = conn.query(sql_teams)
    
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name 
                     for name, info in TEAMS.items() if 'opta_uuid' in info}

    valid_teams = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                valid_teams[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    # --- TOP MENU ---
    st.markdown('<div class="main-title">Fysisk Aktions-Analyse</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    valgt_hold = c1.selectbox("Vælg Hold", sorted(list(valid_teams.keys())))
    valgt_uuid_hold = valid_teams[valgt_hold]

    sql_spillere = f"""
        SELECT DISTINCT TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, e.PLAYER_OPTAUUID
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
        AND e.EVENT_TIMESTAMP >= '2025-07-01'
    """
    df_pl = conn.query(sql_spillere)
    
    if df_pl is None or df_pl.empty:
        st.warning("Ingen spillere fundet.")
        return

    valgt_spiller = c2.selectbox("Vælg Spiller", sorted(df_pl['NAVN'].tolist()))
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    st.markdown("---")

    # --- DATA HENTNING ---
    # Vi henter både aggregeret data (til metrics) og detaljeret data (til pile)
    df_runs = get_detailed_run_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    if df_runs is not None and not df_runs.empty:
        # Hurtige Metrics (Beregnet fra run-data)
        hsr_count = len(df_runs[df_runs['SPEED_CATEGORY'] == 'HSR'])
        sprint_count = len(df_runs[df_runs['SPEED_CATEGORY'] == 'SPRINT'])
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Antal HSR-løb", hsr_count)
        m2.metric("Antal Sprints", sprint_count)
        m3.metric("Kampe analyseret", df_runs['MATCH_DATE'].nunique())

        # TABS TIL VISUALISERING
        t_arrows, t_stats = st.tabs(["Løbsretninger (Pile)", "Data-oversigt"])

        with t_arrows:
            st.write("### Højintensive løbsstier")
            st.caption("Viser start- og slutpositioner for alle HSR og Sprints i sæsonen.")
            
            p_col1, p_col2 = st.columns(2)
            
            with p_col1:
                # TIP: Grønne pile (Offensiv)
                fig_tip = draw_run_pitch(df_runs, 'TIP', '#2ecc71', "TIP (Med bold)")
                st.pyplot(fig_tip)

            with p_col2:
                # OTIP: Røde pile (Defensiv)
                fig_otip = draw_run_pitch(df_runs, 'OTIP', '#e74c3c', "OTIP (Modstander med bold)")
                st.pyplot(fig_otip)
            
            st.info("**Tolkningsguide:** Pilene viser spillerens bevægelsesmønster ved høj fart. Lange pile indikerer omstillingsløb, mens klynger af pile viser spillerens foretrukne arbejdsområder.")

        with t_stats:
            st.write("### Liste over alle højintensive aktioner")
            st.dataframe(df_runs.sort_values('MATCH_DATE', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info(f"Ingen detaljerede løbskoordinater fundet for {valgt_spiller}. Tjek om data er indlæst i tabellen 'SECONDSPECTRUM_RUN_EVENTS'.")

if __name__ == "__main__":
    vis_side()
