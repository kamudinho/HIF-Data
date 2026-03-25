import streamlit as st
import pandas as pd
import seaborn as sns
from mplsoccer import VerticalPitch
from data.data_load import _get_snowflake_conn

# --- CACHED DATA FUNKTIONER ---

@st.cache_data(ttl=3600)
def get_league_teams(tournament_uuid):
    """Henter lynhurtigt en liste over hold i turneringen."""
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    query = f"""
        SELECT DISTINCT CONTESTANTHOME_NAME as name, CONTESTANTHOME_OPTAUUID as uuid 
        FROM {db}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_uuid}'
    """
    return pd.read_sql(query, conn)

@st.cache_data(ttl=600) # Kortere cache så nyeste kampe kommer med
def get_single_team_events(team_uuid, tournament_uuid):
    """Henter KUN events for det valgte hold. Dette er nøglen til fart!"""
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    query = f"""
        SELECT 
            EVENT_TYPEID, PLAYER_NAME, 
            EVENT_X AS LOCATIONX, EVENT_Y AS LOCATIONY
        FROM {db}.OPTA_EVENTS
        WHERE EVENT_CONTESTANT_OPTAUUID = '{team_uuid}'
        AND MATCH_OPTAUUID IN (
            SELECT MATCH_OPTAUUID FROM {db}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_uuid}'
        )
        AND EVENT_TYPEID IN (1, 4, 8, 49, 13, 14, 15, 16)
    """
    return pd.read_sql(query, conn)

# --- HOVEDFUNKTION (LAYOUT BEVARET) ---

def vis_side(dp_fra_main=None):
    # Vi bruger NordicBet UUID som standard (fra din konfiguration)
    NORDICBET_UUID = "dyjr458hcmrcy87fsabfsy87o"
    
    # 1. Vælg hold (Kører lynhurtigt da den kun henter navne)
    df_teams = get_league_teams(NORDICBET_UUID)
    valgt_hold_navn = st.selectbox("Vælg modstander:", sorted(df_teams['name'].unique()))
    valgt_uuid = df_teams[df_teams['name'] == valgt_hold_navn]['uuid'].iloc[0]

    # 2. Hent kun data for det valgte hold
    with st.spinner(f"Analyserer {valgt_hold_navn}..."):
        df_hold_events = get_single_team_events(valgt_uuid, NORDICBET_UUID)

    if df_hold_events.empty:
        st.warning("Ingen data fundet.")
        return

    # --- DIN ORIGINALE VISUALISERING ---
    tabs = st.tabs(["Offensiv", "Defensiv", "Spiller-stats"])
    pitch = VerticalPitch(pitch_type='opta', pitch_color='white', line_color='#333333')

    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Afslutningsmønster**")
            fig, ax = pitch.draw()
            shots = df_hold_events[df_hold_events['EVENT_TYPEID'].isin([13,14,15,16])]
            if not shots.empty:
                pitch.scatter(shots.LOCATIONX, shots.LOCATIONY, ax=ax, color='#df003b', alpha=0.6)
            st.pyplot(fig)
        with c2:
            st.write("**Pass Heatmap**")
            fig, ax = pitch.draw()
            passes = df_hold_events[df_hold_events['EVENT_TYPEID'] == 1]
            if len(passes) > 5:
                sns.kdeplot(x=passes.LOCATIONY, y=passes.LOCATIONX, fill=True, cmap='Reds', ax=ax, alpha=0.5)
            st.pyplot(fig)

    with tabs[1]:
        st.write("**Defensive aktioner**")
        fig, ax = pitch.draw()
        # 4=Tackle, 8=Interception, 49=Ball Recovery
        defensive = df_hold_events[df_hold_events['EVENT_TYPEID'].isin([4, 8, 49])]
        if len(defensive) > 5:
            sns.kdeplot(x=defensive.LOCATIONY, y=defensive.LOCATIONX, fill=True, cmap='Blues', ax=ax, alpha=0.5)
        st.pyplot(fig)

    with tabs[2]:
        st.write(f"Mest aktive spillere ({valgt_hold_navn})")
        st.dataframe(df_hold_events['PLAYER_NAME'].value_counts().head(10))
