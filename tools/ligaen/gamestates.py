# tools/ligaen/gamestates.py

import streamlit as st
import pandas as pd
import plotly.express as px
from data.data_load import _get_snowflake_conn
from data.sql.teams import hent_hold_gamestate_tid

def vis_side():
    """
    Hovedfunktion der kaldes af appen. Viser holdenes spilletid fordelt på
    Winning, Drawing og Losing baseret på den rigtige minut-for-minut SQL-logik.
    """
    st.markdown("#### Holdenes Gamestates (Førende / Uafgjort / Bagud)")
    st.caption("Oversigt over andelen af spilletiden holdene tilbringer i henholdsvis Winning, Drawing og Losing.")

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake.")
        return

    # Standard kalender-UUID for turneringen
    calendar_uuid = "2mb332vncy4450vu14paj8844"

    # Hent data ved at kalde funktionen fra teams.py
    with st.spinner("Henter gamestate-data fra Snowflake..."):
        try:
            df = hent_hold_gamestate_tid(conn, calendar_uuid)
        except Exception as e:
            if "390111" in str(e) or "Session no longer exists" in str(e):
                st.warning("Sessionen udløbet. Genopretter forbindelse...")
                st.cache_data.clear()
                new_conn = _get_snowflake_conn()
                df = hent_hold_gamestate_tid(new_conn, calendar_uuid)
            else:
                st.error(f"Fejl ved hentning af data: {e}")
                return

    if df.empty:
        st.info("Ingen gamestate-data fundet for denne kalender.")
        return

    # Sørg for at data er sorteret efter mest tid i føring (Winning %)
    df_grouped = df.sort_values(by='WINNING_PCT', ascending=False)

    # Plotly stabeldiagram (Stacked bar chart) ligesom Opta Analyst
    fig = px.bar(
        df_grouped,
        x=['LOSING_PCT', 'DRAWING_PCT', 'WINNING_PCT'],
        y='TEAM_NAME',
        orientation='h',
        title="Procent af spilletid i hver Game State",
        labels={'value': 'Procent (%)', 'variable': 'Game State', 'TEAM_NAME': 'Hold'},
        color_discrete_map={
            'LOSING_PCT': '#f87171',   # Rød
            'DRAWING_PCT': '#cbd5e1',  # Grå
            'WINNING_PCT': '#4ade80'   # Grøn
        }
    )
    
    # Tilpas kolonnenavne i legenden til pænere tekst
    names = {'LOSING_PCT': 'Losing', 'DRAWING_PCT': 'Drawing', 'WINNING_PCT': 'Winning'}
    fig.for_each_trace(lambda t: t.update(name = names.get(t.name, t.name)))

    fig.update_layout(
        barmode='stack', 
        xaxis_range=[0, 100],
        legend_title_text='Game State',
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
