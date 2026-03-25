import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
from data.data_load import _get_snowflake_conn

# --- 1. DATA ADGANG (Hurtig & Cached) ---
@st.cache_data(ttl=3600)
def load_opta_base_data(tournament_uuid):
    """Henter kun de nødvendige kolonner for hele ligaen én gang."""
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    # Vi henter kun de kolonner, vi rent faktisk tegner på banen
    query = f"""
        SELECT 
            MATCH_OPTAUUID, 
            EVENT_CONTESTANT_OPTAUUID, 
            EVENT_TYPEID, 
            PLAYER_NAME, 
            EVENT_X AS LOCATIONX, 
            EVENT_Y AS LOCATIONY
        FROM {db}.OPTA_EVENTS
        WHERE MATCH_OPTAUUID IN (
            SELECT DISTINCT MATCH_OPTAUUID FROM {db}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_uuid}'
        )
        AND EVENT_TYPEID IN (1, 4, 5, 8, 49, 13, 14, 15, 16)
    """
    df = pd.read_sql(query, conn)
    return df

@st.cache_data(ttl=3600)
def load_match_metadata(tournament_uuid):
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    query = f"""
        SELECT MATCH_OPTAUUID, CONTESTANTHOME_NAME, CONTESTANTAWAY_NAME, 
               CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID
        FROM {db}.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_uuid}'
    """
    return pd.read_sql(query, conn)

# --- 2. SELVE SIDEN ---
def vis_side(analysis_package=None):
    # Konstanter (Bør måske komme fra dine indstillinger)
    NORDICBET_UUID = "dyjr458hcmrcy87fsabfsy87o"
    
    st.subheader("Modstander Analyse - Direkte Opta Data")

    # 1. Load Metadata (Hurtigt)
    df_matches = load_match_metadata(NORDICBET_UUID)
    
    # Byg holdliste til selectbox
    all_teams = pd.concat([
        df_matches[['CONTESTANTHOME_NAME', 'CONTESTANTHOME_OPTAUUID']].rename(columns={'CONTESTANTHOME_NAME': 'name', 'CONTESTANTHOME_OPTAUUID': 'uuid'}),
        df_matches[['CONTESTANTAWAY_NAME', 'CONTESTANTAWAY_OPTAUUID']].rename(columns={'CONTESTANTAWAY_NAME': 'name', 'CONTESTANTAWAY_OPTAUUID': 'uuid'})
    ]).drop_duplicates()
    
    col1, col2 = st.columns(2)
    with col1:
        valgt_hold_navn = st.selectbox("Vælg hold til analyse:", sorted(all_teams['name'].tolist()))
        valgt_uuid = all_teams[all_teams['name'] == valgt_hold_navn]['uuid'].iloc[0]

    # 2. Load Events (Kun hvis de ikke er i cache)
    with st.spinner("Henter hændelser fra Snowflake..."):
        df_all_events = load_opta_base_data(NORDICBET_UUID)
    
    # 3. Filtrering lokalt i Python (Lynhurtigt efter load)
    df_hold_events = df_all_events[df_all_events['EVENT_CONTESTANT_OPTAUUID'] == valgt_uuid].copy()

    if df_hold_events.empty:
        st.warning(f"Ingen data fundet for {valgt_hold_navn}")
        return

    # 4. Visualisering
    tabs = st.tabs(["Offensiv", "Defensiv", "Spiller-stats"])
    
    pitch = VerticalPitch(pitch_type='opta', pitch_color='white', line_color='#333333')

    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Afslutningsmønster**")
            fig, ax = pitch.draw()
            shots = df_hold_events[df_hold_events['EVENT_TYPEID'].isin([13,14,15,16])]
            if not shots.empty:
                pitch.scatter(shots.LOCATIONX, shots.LOCATIONY, ax=ax, color='red', alpha=0.5)
            st.pyplot(fig)
        
        with c2:
            st.write("**Opbygning (Pass Heatmap)**")
            fig, ax = pitch.draw()
            passes = df_hold_events[df_hold_events['EVENT_TYPEID'] == 1]
            if len(passes) > 5:
                sns.kdeplot(x=passes.LOCATIONY, y=passes.LOCATIONX, fill=True, cmap='Reds', ax=ax, alpha=0.5)
            st.pyplot(fig)

    with tabs[1]:
        st.write("**Defensive aktioner (Erobringer & Tacklinger)**")
        fig, ax = pitch.draw()
        defensive = df_hold_events[df_hold_events['EVENT_TYPEID'].isin([4, 8, 49])]
        if len(defensive) > 5:
            sns.kdeplot(x=defensive.LOCATIONY, y=defensive.LOCATIONX, fill=True, cmap='Blues', ax=ax, alpha=0.5)
        st.pyplot(fig)

    with tabs[2]:
        st.write(f"Top 5 mest aktive spillere for {valgt_hold_navn}")
        stats = df_hold_events['PLAYER_NAME'].value_counts().head(5)
        st.table(stats)
