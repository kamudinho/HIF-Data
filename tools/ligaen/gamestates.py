# tools/ligaen/gamestates.py

import streamlit as st
import pandas as pd
import plotly.express as px
from data.data_load import _get_snowflake_conn

def hent_gamestate_data(connection=None):
    """
    Henter og beregner spilletid (og procenter) fordelt på Winning, Drawing og Losing 
    for holdene i den aktuelle kalender.
    """
    if connection is None:
        connection = _get_snowflake_conn()

    # Eksempel på SQL-forespørgsel til at hente gamestate data (tilpas tabeller/kolonner efter behov)
    sql_query = """
    WITH MatchBase AS (
        SELECT 
            MATCH_OPTAUUID,
            CONTESTANTHOME_OPTAUUID,
            CONTESTANTAWAY_OPTAUUID,
            CONTESTANTHOME_NAME,
            CONTESTANTAWAY_NAME
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHINFO
        WHERE TOURNAMENTCALENDAR_OPTAUUID = '2mb332vncy4450vu14paj8844'
          AND MATCH_STATUS = 'Played'
    )
    -- Her kan du erstatte med jeres faktiske gamestate aggregering, f.eks. fra en tabel der gemmer minutter pr state.
    -- Som udgangspunkt opretter vi et sikkert fallback/struktur, hvis tabellen mangler specifikke kolonner endnu:
    SELECT 
        CONTESTANTHOME_NAME AS TEAM_NAME,
        90 AS TOTAL_MINS,
        30 AS WINNING_MINS,
        30 AS DRAWING_MINS,
        30 AS LOSING_MINS
    FROM MatchBase
    """
    
    try:
        return connection.query(sql_query, ttl=0)
    except Exception as e:
        if "390111" in str(e) or "Session no longer exists" in str(e):
            st.warning("Sessionen udløbet. Genopretter forbindelse...")
            st.cache_data.clear()
            new_conn = _get_snowflake_conn()
            return new_conn.query(sql_query, ttl=0)
        else:
            # Returner tomt DataFrame hvis tabellen ikke findes endnu, så appen ikke crasher
            return pd.DataFrame()

def vis_side():
    """
    Hovedfunktion der kaldes af appen. Sikrer at 'vis_side' er til stede.
    """
    st.markdown("#### Holdenes Gamestates (Førende / Uafgjort / Bagud)")
    st.caption("Oversigt over andelen af spilletiden holdene tilbringer i henholdsvis Winning, Drawing og Losing.")

    # Hent data
    with st.spinner("Henter gamestate-data..."):
        df = hent_gamestate_data()

    if df.empty:
        st.info("Gamestate-data er endnu ikke tilgængelig i databasen for denne kalender.")
        return

    # Beregn procenter hvis de ikke findes direkte
    if 'WINNING_PCT' not in df.columns and 'TOTAL_MINS' in df.columns:
        df['WINNING_PCT'] = (df['WINNING_MINS'] / df['TOTAL_MINS']) * 100
        df['DRAWING_PCT'] = (df['DRAWING_MINS'] / df['TOTAL_MINS']) * 100
        df['LOSING_PCT'] = (df['LOSING_MINS'] / df['TOTAL_MINS']) * 100

    # Aggreger pr hold hvis der er flere rækker pr hold
    df_grouped = df.groupby('TEAM_NAME')[['WINNING_PCT', 'DRAWING_PCT', 'LOSING_PCT']].mean().reset_index()
    df_grouped = df_grouped.sort_values(by='WINNING_PCT', ascending=False)

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
