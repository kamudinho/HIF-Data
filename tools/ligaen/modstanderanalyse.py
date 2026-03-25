import streamlit as st
import pandas as pd
import seaborn as sns
from mplsoccer import VerticalPitch
from data.data_load import _get_snowflake_conn

@st.cache_data(ttl=3600)
def get_league_teams(tournament_uuid):
    """Henter holdliste og sikrer korrekte kolonnenavne."""
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    # Vi henter både hjemme- og udehold for at få alle med
    query = f"""
        SELECT DISTINCT CONTESTANTHOME_NAME as TEAM_NAME, CONTESTANTHOME_OPTAUUID as TEAM_UUID 
        FROM {db}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_uuid}'
        UNION
        SELECT DISTINCT CONTESTANTAWAY_NAME as TEAM_NAME, CONTESTANTAWAY_OPTAUUID as TEAM_UUID 
        FROM {db}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_uuid}'
    """
    df = pd.read_sql(query, conn)
    return df

@st.cache_data(ttl=600)
def get_single_team_events(team_uuid, tournament_uuid):
    """Henter events for det specifikke hold."""
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

def vis_side(dp=None):
    # Brug din faste UUID for NordicBet Ligaen
    NORDICBET_UUID = "dyjr458hcmrcy87fsabfsy87o"
    
    # 1. Hent hold (Fejlsikret)
    df_teams = get_league_teams(NORDICBET_UUID)
    
    if df_teams.empty:
        st.error("Kunne ikke hente holdliste fra Snowflake.")
        return

    # Sørg for at vi bruger de rigtige kolonnenavne fra SQL'en
    hold_liste = sorted(df_teams['TEAM_NAME'].unique())
    valgt_hold_navn = st.selectbox("Vælg modstander:", hold_liste)
    
    # Find UUID baseret på det valgte navn
    valgt_uuid = df_teams[df_teams['TEAM_NAME'] == valgt_hold_navn]['TEAM_UUID'].iloc[0]

    # 2. Hent data kun for det valgte hold
    with st.spinner(f"Henter data for {valgt_hold_navn}..."):
        df_hold_events = get_single_team_events(valgt_uuid, NORDICBET_UUID)

    if df_hold_events.empty:
        st.warning(f"Ingen hændelser fundet for {valgt_hold_navn} i denne sæson.")
        return

    # --- Layout (Tabs) ---
    tabs = st.tabs(["Med bold", "Mod bold", "Top 5-stats"])
    pitch = VerticalPitch(pitch_type='opta', pitch_color='white', line_color='#333333')

    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Afslutninger**")
            fig, ax = pitch.draw()
            shots = df_hold_events[df_hold_events['EVENT_TYPEID'].isin([13,14,15,16])]
            if not shots.empty:
                pitch.scatter(shots.LOCATIONX, shots.LOCATIONY, ax=ax, color='#df003b', alpha=0.6)
            st.pyplot(fig)
        with c2:
            st.write("**Passmap**")
            fig, ax = pitch.draw()
            passes = df_hold_events[df_hold_events['EVENT_TYPEID'] == 1]
            if len(passes) > 5:
                sns.kdeplot(x=passes.LOCATIONY, y=passes.LOCATIONX, fill=True, cmap='Reds', ax=ax, alpha=0.5)
            st.pyplot(fig)

    with tabs[1]:
        st.write("**Defensive aktioner (Tacklinger/Erobringer)**")
        fig, ax = pitch.draw()
        defensive = df_hold_events[df_hold_events['EVENT_TYPEID'].isin([4, 8, 49])]
        if len(defensive) > 5:
            sns.kdeplot(x=defensive.LOCATIONY, y=defensive.LOCATIONX, fill=True, cmap='Blues', ax=ax, alpha=0.5)
        st.pyplot(fig)

    with tabs[2]:
        st.write(f"Mest aktive spillere ({valgt_hold_navn})")
        st.dataframe(df_hold_events['PLAYER_NAME'].value_counts().head(10), use_container_width=True)
