import streamlit as st
import pandas as pd
import io
import base64
from mplsoccer import Pitch
# Importér din funktion (tilpas stien hvis nødvendigt)
from data.sql.liga_spillere import hent_match_og_haendelsesdata
from utils.helpers import draw_player_info_box

# ---------------------------------------------------------------------------
# KONSTANTER
# ---------------------------------------------------------------------------
TOUCH_IDS = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
DESCRIPTIONS = {
    "Heatmap": "Viser spillerens generelle bevægelsesmønster.",
    "Berøringer": "Alle aktioner med boldkontakt.",
    "Afslutninger": "Skudforsøg (Mål = firkant, skud = cirkel).",
    "Defensive aktioner": "Tacklinger, erobringer og opsnappede afleveringer.",
    "Offensive pasninger": "Fremadrettede pasninger til sidste tredjedel.",
    "Alle aktioner": "Oversigt over samtlige aktionstyper."
}

def render_spilleraktioner(df_spiller, valgt_spiller, hold_logo, primær_farve, spiller_position, valgt_player_uuid, season_name="2026/2027"):
    """Selve logikken der tegner interfacet."""
    
    if df_spiller is None or df_spiller.empty:
        st.info("Ingen spilledata fundet for den valgte spiller.")
        return

    # Statistikker (som i din oprindelige kode)
    df_filtreret = df_spiller[~df_spiller['action_label'].isin(['Pasning', 'Indkast'])] # Bemærk små bogstaver fra din SQL-funktion
    akt_stats = df_filtreret.groupby('action_label').agg(Total=('outcome', 'count'), Succes=('outcome', 'sum')).sort_values('Total', ascending=False)

    c1, c2, c3 = st.columns([1, 0.05, 2.2])
    
    with c1:
        st.subheader(valgt_spiller)
        st.metric("Total aktioner", len(df_spiller))
        # ... (Her kan du indsætte dine metrikker fra tidligere)

    with c3:
        visning = st.selectbox("Visning", list(DESCRIPTIONS.keys()), key=f"sel_{valgt_player_uuid}")
        
        pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        # Plot logik
        df_plot = df_spiller.dropna(subset=['event_x', 'event_y'])
        if visning == "Heatmap":
            pitch.kdeplot(df_plot.event_x, df_plot.event_y, ax=ax, cmap='Blues', fill=True, levels=50)
        
        st.pyplot(fig)

def vis_side(conn, db_navn, hold_uuid, liga_ids, navne_map, hold_logo, primær_farve):
    """
    Henter data og renderer siden. 
    Dette er den funktion du kalder i din hovedapp.
    """
    # 1. Hent alt data
    with st.spinner("Henter spillerdata..."):
        df_all, df_expected, df_db_stats = hent_match_og_haendelsesdata(conn, db_navn, hold_uuid, liga_ids, navne_map)
    
    # 2. Vælg spiller
    spillere = df_all['visningsnavn'].unique()
    valgt_navn = st.selectbox("Vælg spiller", spillere)
    
    # 3. Filtrer data til den valgte spiller
    df_spiller = df_all[df_all['visningsnavn'] == valgt_navn].copy()
    player_uuid = df_spiller['player_optauuid'].iloc[0]
    
    # 4. Render
    render_spilleraktioner(
        df_spiller=df_spiller,
        valgt_spiller=valgt_navn,
        hold_logo=hold_logo,
        primær_farve=primær_farve,
        spiller_position="Midfielder", # Kan udvides
        valgt_player_uuid=player_uuid,
        season_name="2026/2027"
    )

# --- HVORDAN DU KALDER DEN I DIN HOVEDAPP ---
# vis_side(conn, "HVIDOVRE_DB", "7490", (328,), { ... }, logo, "#0000FF")
