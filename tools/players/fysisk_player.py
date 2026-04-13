import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
# Vi fjerner de lange UUIDs midlertidigt for at teste med de simple liga-id'er
LIGA_IDS = "('335', '328', '329', '43319', '331')"
CURRENT_SEASON = "2025/2026"

def get_physical_data(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid', '56fa29c7-3a48-4186-9d14-dbf45fbc78d9')
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    
    # Vi søger bredt på navnet for at være sikre
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT 
            p.MATCH_DATE,
            ANY_VALUE(p.MATCH_TEAMS) as MATCH_TEAMS,
            MAX(p.MINUTES) as MINUTES,
            SUM(p.DISTANCE) as DISTANCE,
            SUM(p."HIGH SPEED RUNNING") as HSR,
            SUM(p.SPRINTING) as SPRINTING,
            MAX(p.TOP_SPEED) as TOP_SPEED,
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS) as HI_RUNS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        WHERE (({name_conditions}) OR ("optaId" LIKE '%{clean_id}%'))
          AND p.MATCH_DATE >= '2025-07-01'
        GROUP BY p.MATCH_DATE, p.PLAYER_NAME
        ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side(dp=None):
    st.set_page_config(layout="wide") # Sikrer at siden bruger hele bredden
    
    conn = _get_snowflake_conn()
    if not conn:
        st.error("Kunne ikke oprette forbindelse til Snowflake.")
        return

    # --- SIDEBAR ---
    st.sidebar.title("Fysisk Analyse")
    
    # Vi henter hold direkte fra TEAMS mappingen i stedet for databasen for at sikre, menuen virker
    hold_liste = sorted(list(TEAMS.keys()))
    valgt_hold = st.sidebar.selectbox("Vælg Hold", hold_liste)
    
    # Hent holdets UUID fra din TEAMS mapping
    valgt_uuid_hold = TEAMS[valgt_hold].get('opta_uuid')
    
    # Hent spillere for det valgte hold
    with st.spinner(f"Henter spillere for {valgt_hold}..."):
        sql_spillere = f"""
            SELECT DISTINCT 
                TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as NAVN, 
                e.PLAYER_OPTAUUID
            FROM {DB}.OPTA_EVENTS e
            JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
        """
        df_pl = conn.query(sql_spillere)
    
    if df_pl is None or df_pl.empty:
        st.sidebar.warning(f"Ingen spillere fundet for {valgt_hold} i OPTA_EVENTS.")
        return

    valgt_spiller = st.sidebar.selectbox("Vælg Spiller", sorted(df_pl['NAVN'].tolist()))
    valgt_player_uuid = df_pl[df_pl['NAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]

    # --- HOVEDSIDE ---
    st.title(f"Fysisk Profil: {valgt_spiller}")
    
    df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    if df_phys is not None and not df_phys.empty:
        # Metrics
        latest = df_phys.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Seneste Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
        c2.metric("HSR", f"{int(latest['HSR'])} m")
        c3.metric("Topfart", f"{round(df_phys['TOP_SPEED'].max(), 1)} km/t")
        c4.metric("Kampe", len(df_phys))

        # Graf
        st.subheader("Sæsonudvikling (HSR)")
        df_chart = df_phys.sort_values('MATCH_DATE')
        fig = go.Figure(go.Bar(
            x=df_chart['MATCH_DATE'], 
            y=df_chart['HSR'],
            marker_color='#cc0000'
        ))
        fig.update_layout(plot_bgcolor="white", height=350)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df_phys, use_container_width=True)
    else:
        st.warning(f"Ingen fysisk data fundet i SECONDSPECTRUM for {valgt_spiller}.")
        st.info("Tjek om spillerens navn i Second Spectrum matcher navnet i Opta.")

if __name__ == "__main__":
    vis_side()
