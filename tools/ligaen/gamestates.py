# tools/ligaen/gamestates.py

import streamlit as st
import pandas as pd
import plotly.express as px
from data.data_load import _get_snowflake_conn
from data.sql.teams import hent_hold_gamestate_tid

def vis_side():
    """
    Hovedfunktion der kaldes af appen. Viser det korrekte stabeldiagram for holdenes gamestates.
    """
    st.markdown("#### Holdenes Gamestates (Førende / Uafgjort / Bagud)")
    st.caption("Oversigt over andelen af spilletiden holdene tilbringer i henholdsvis Winning, Drawing og Losing.")

    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake.")
        return

    calendar_uuid = "2mb332vncy4450vu14paj8844"

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

    # Sorter holdene efter mest tid i føring (Winning %)
    df = df.sort_values(by='WINNING_PCT', ascending=True)

    # Omstrukturer data til 'long'-format, så Plotly kan lave et ægte stabeldiagram
    df_melted = pd.melt(
        df,
        id_vars=['TEAM_NAME'],
        value_vars=['LOSING_PCT', 'DRAWING_PCT', 'WINNING_PCT'],
        var_name='GAME_STATE',
        value_name='PERCENTAGE'
    )

    # Pænere navne til legenden
    state_mapping = {
        'LOSING_PCT': 'Losing',
        'DRAWING_PCT': 'Drawing',
        'WINNING_PCT': 'Winning'
    }
    df_melted['GAME_STATE'] = df_melted['GAME_STATE'].map(state_mapping)

    # Plotly stabeldiagram
    fig = px.bar(
        df_melted,
        x='PERCENTAGE',
        y='TEAM_NAME',
        color='GAME_STATE',
        orientation='h',
        title="Procent af spilletid i hver Game State",
        labels={'PERCENTAGE': 'Procent (%)', 'TEAM_NAME': 'Hold', 'GAME_STATE': 'Game State'},
        color_discrete_map={
            'Losing': '#f87171',   # Rød
            'Drawing': '#cbd5e1',  # Grå
            'Winning': '#4ade80'   # Grøn
        }
    )

    fig.update_layout(
        barmode='stack', 
        xaxis_range=[0, 100],
        legend_title_text='Game State',
        height=600,
        yaxis={'categoryorder': 'array', 'categoryarray': df['TEAM_NAME'].tolist()}
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    vis_side()
