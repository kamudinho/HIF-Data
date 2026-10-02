# tools/ligaen.py
import streamlit as st
import pandas as pd
import plotly.express as px
from data.sql.teams import hent_liga_stilling, hent_hold_gamestate_tid
from data.data_load import _get_snowflake_conn

def render_page(calendar_uuid: str):
    st.title("📊 Holdenes Gamestates (Førende / Uafgjort / Bagud)")
    st.markdown("Oversigt over hvor stor en andel af spilletiden holdene tilbringer i henholdsvis *Losing*, *Drawing* og *Winning*.")

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake.")
        return

    with st.spinner("Henter data for spilletid i forskellige stater..."):
        df_stilling = hent_liga_stilling(conn, calendar_uuid)
        df_gamestate = hent_hold_gamestate_tid(conn, calendar_uuid)

    if df_stilling.empty:
        st.warning("Ingen holddata fundet for den valgte kalender.")
        return

    # Eksempel på visning af stilling / tabellen
    st.subheader("Liga Stilling")
    st.dataframe(df_stilling[['POSITION', 'TEAM_NAME', 'PL', 'W', 'D', 'L', 'PTS']], use_container_width=True)

    st.markdown("---")
    st.subheader("Spilletid fordelt på Game State")
    
    # Her kan du bygge visualiseringen, når gamestate-dataene er fuldt udbygget i SQL.
    # Nedenfor er et eksempel på hvordan et stabeldiagram (stacked bar chart) kan sættes op i Plotly:
    
    if not df_gamestate.empty and 'LOSING_PCT' in df_gamestate.columns:
        # Hvis data indeholder procenter for losing, drawing, winning:
        fig = px.bar(
            df_gamestate, 
            x=['LOSING_PCT', 'DRAWING_PCT', 'WINNING_PCT'], 
            y='TEAM_NAME', 
            orientation='h',
            title="Procent af tid i hver game state",
            labels={'value': 'Procent (%)', 'variable': 'Game State', 'TEAM_NAME': 'Hold'},
            color_discrete_map={
                'LOSING_PCT': '#f87171',   # Rødlig
                'DRAWING_PCT': '#cbd5e1',  # Grålig
                'WINNING_PCT': '#4ade80'   # Grønlig
            }
        )
        fig.update_layout(barmode='stack', xaxis_range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Gamestate-detaljer er under opbygning. SQL-funktionen kan udvides, når minut-for-minut måldata tilknyttes.")

if __name__ == "__main__":
    # Hvis siden køres direkte eller integreres via din main navigation
    calendar_uuid = "2mb332vncy4450vu14paj8844" # Standard / din aktiverede kalender
    render_page(calendar_uuid)
