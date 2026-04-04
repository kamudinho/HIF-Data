import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
from data.utils.mapping import OPTA_EVENT_TYPES

# --- HJÆLPEFUNKTION TIL HEATMAPS ---
def plot_pass_heatmap(df, team_name, direction="up"):
    """
    Tegner et heatmap over pasninger. 
    'up' = Gennembrud (mod mål foroven)
    'down' = Opbygning (mod mål forneden)
    """
    # Filtrer kun pasninger (Type 1)
    pass_df = df[df['EVENT_TYPEID'] == 1].copy()
    
    if direction == "up":
        # Lodret pitch - målet er i toppen (y=100)
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw(figsize=(8, 10))
        # Vi bruger hexbin for et skarpt analytisk look, men kan også bruge kdeplot
        pitch.hexbin(pass_df.EVENT_X, pass_df.EVENT_Y, edgecolors='#ffffff', 
                     gridsize=(15, 15), cmap='Reds', alpha=0.8, ax=ax)
        ax.set_title(f"Gennembrudspasninger: {team_name}", fontsize=14, pad=20)
    else:
        # Lodret pitch - men vi inverterer aksen så det vender "nedad"
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#BDBDBD')
        fig, ax = pitch.draw(figsize=(8, 10))
        # Ved at bruge half=True og lade den tegne standard, vender målet opad. 
        # For at få det til at vende nedad, inverterer vi viewet.
        ax.invert_yaxis()
        ax.invert_xaxis()
        pitch.hexbin(pass_df.EVENT_X, pass_df.EVENT_Y, edgecolors='#ffffff', 
                     gridsize=(15, 15), cmap='Blues', alpha=0.8, ax=ax)
        ax.set_title(f"Opbygningsspil (fremadrettet): {team_name}", fontsize=14, pad=20)
    
    return fig

# --- OPGRADERET vis_side FUNKTION ---
def vis_side(dp=None):
    conn = _get_snowflake_conn()
    if not conn: return

    # 3.1 Initialisering (Hvidovre-app værdier)
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'")
    ids = df_teams_raw['CONTESTANTHOME_OPTAUUID'].unique()
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    team_map = {mapping_lookup.get(str(u).lower().replace('t','')): u for u in ids if mapping_lookup.get(str(u).lower().replace('t',''))}

    col_spacer, col_hold = st.columns([3, 1])
    valgt_hold = col_hold.selectbox("Vælg hold", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid = team_map[valgt_hold]

    # Hent alle events for det valgte hold i sæsonen til heatmaps
    with st.spinner("Genererer data..."):
        sql_all_events = f"""
        SELECT EVENT_X, EVENT_Y, EVENT_TYPEID, PLAYER_NAME
        FROM {DB}.OPTA_EVENTS 
        WHERE EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid}'
        AND TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
        AND EVENT_TYPEID IN (1, 16) -- Pasninger og mål
        """
        df_total = conn.query(sql_all_events)

    # Tabs (Tilføjet "MED BOLD")
    t1, t2, t3, t4 = st.tabs(["EVENTS", "MÅL-SEKVENSER", "SPILLEROVERSIGT", "MED BOLD"])

    # ... (t1, t2, t3 koden er den samme som før) ...

    with t4:
        st.subheader(f"Positionsanalyse: {valgt_hold}")
        
        col_heat1, col_heat2 = st.columns(2)
        
        with col_heat1:
            st.write("**Opbygning (Fremadrettet)**")
            fig_down = plot_pass_heatmap(df_total, valgt_hold, direction="down")
            st.pyplot(fig_down)
            st.caption("Viser intensiteten af pasninger i opbygningsfasen (orienteret nedad).")

        with col_heat2:
            st.write("**Gennembrud (Mod mål)**")
            fig_up = plot_pass_heatmap(df_total, valgt_hold, direction="up")
            st.pyplot(fig_up)
            st.caption("Viser hvor holdet er farligst i de afgørende afleveringer mod modstanderens felt.")

        # Ekstra: Pasningsstatistik
        st.divider()
        pass_count = len(df_total[df_total['EVENT_TYPEID'] == 1])
        st.metric("Total antal pasninger i sæsonen", f"{pass_count:,}")
