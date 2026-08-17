import streamlit as st
import pandas as pd
import io
import base64
from mplsoccer import Pitch
from data.sql.liga_spillere import hent_match_og_haendelsesdata
from utils.helpers import draw_player_info_box

def render_spilleraktioner(df_spiller, valgt_spiller, hold_logo, primær_farve, spiller_position, valgt_player_uuid, season_name="2026/2027"):
    """Renderer interfacet (Logik adskilt fra dataindlæsning)."""
    if df_spiller is None or df_spiller.empty:
        st.info("Ingen spilledata fundet for den valgte spiller.")
        return

    # Sørg for at vi bruger små bogstaver (da din SQL-funktion konverterer til lowercase)
    df_spiller.columns = df_spiller.columns.str.lower()
    
    # Resten af din logik her...
    st.subheader(valgt_spiller)
    st.write(f"Antal aktioner: {len(df_spiller)}")
    
    # Eksempel på banetegning
    pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
    fig, ax = pitch.draw(figsize=(10, 7))
    st.pyplot(fig)

def vis_side(conn=None, db_navn=None, hold_uuid=None, liga_ids=None, navne_map=None, hold_logo=None, primær_farve=None):
    """
    Wrapper der automatisk henter argumenter fra session_state, 
    hvis de ikke sendes med i kaldet.
    """
    # 1. Hent fra argumenter eller session_state
    conn = conn or st.session_state.get('conn')
    db_navn = db_navn or st.session_state.get('db_navn')
    hold_uuid = hold_uuid or st.session_state.get('hold_uuid')
    liga_ids = liga_ids or st.session_state.get('liga_ids')
    navne_map = navne_map or st.session_state.get('navne_map')
    hold_logo = hold_logo or st.session_state.get('hold_logo')
    primær_farve = primær_farve or st.session_state.get('primær_farve', '#1f77b4')

    # Validering
    if any(v is None for v in [conn, db_navn, hold_uuid, liga_ids]):
        st.error("Mangler database-konfiguration. Sørg for at conn, db_navn, hold_uuid og liga_ids er sat.")
        return

    # 2. Hent data
    @st.cache_data(ttl=3600)
    def load_all_data(conn, db, uuid, ids, mapping):
        return hent_match_og_haendelsesdata(conn, db, uuid, ids, mapping)

    df_all, _, _ = load_all_data(conn, db_navn, hold_uuid, liga_ids, navne_map)

    # 3. Vælg spiller
    spillere = sorted(df_all['visningsnavn'].unique())
    valgt_navn = st.selectbox("Vælg spiller", spillere, key="spiller_selector")
    
    # 4. Filtrer
    df_spiller = df_all[df_all['visningsnavn'] == valgt_navn].copy()
    player_uuid = df_spiller['player_optauuid'].iloc[0]
    
    # 5. Render
    render_spilleraktioner(
        df_spiller=df_spiller,
        valgt_spiller=valgt_navn,
        hold_logo=hold_logo,
        primær_farve=primær_farve,
        spiller_position="Midfielder", 
        valgt_player_uuid=player_uuid,
        season_name="2026/2027"
    )
