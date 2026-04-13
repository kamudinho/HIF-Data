import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from data.data_load import _get_snowflake_conn
from mplsoccer import Pitch
# ... (øvrige imports fra din eksisterende kode)

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
HVIDOVRE_SSIID = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'

def get_advanced_physical_data(player_name, player_opta_uuid, db_conn):
    """ Henter avanceret fysisk data inkl. TIP, OTIP og BOP """
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    
    sql = f"""
    WITH hvidovre_ids AS (
        SELECT DISTINCT
            m.MATCH_SSIID, 
            f.value:"optaId"::string AS opta_id
        FROM {DB}.SECONDSPECTRUM_GAME_METADATA m,
        LATERAL FLATTEN(input => CASE 
            WHEN m.HOME_SSIID = '{HVIDOVRE_SSIID}' THEN m.HOME_PLAYERS 
            ELSE m.AWAY_PLAYERS 
        END) f
        WHERE m.HOME_SSIID = '{HVIDOVRE_SSIID}' 
           OR m.AWAY_SSIID = '{HVIDOVRE_SSIID}'
    )
    SELECT 
        p.MATCH_DATE, p.MATCH_TEAMS, p.PLAYER_NAME, p.MINUTES,
        p.DISTANCE, p.TOP_SPEED,
        p.WALKING, p.JOGGING, p.RUNNING, 
        p."HIGH SPEED RUNNING" AS DISTANCE_HSR,
        p.SPRINTING AS DISTANCE_SPRINT,
        p.NO_OF_HIGH_INTENSITY_RUNS AS HI_RUNS_TOTAL,
        p.DISTANCE_TIP, p.DISTANCE_OTIP, p.DISTANCE_BOP,
        p.NO_OF_HIGH_INTENSITY_RUNS_TIP AS HI_RUNS_TIP,
        p.NO_OF_HIGH_INTENSITY_RUNS_OTIP AS HI_RUNS_OTIP,
        p.MATCH_SSIID
    FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
    INNER JOIN hvidovre_ids h 
        ON p.MATCH_SSIID = h.MATCH_SSIID 
        AND p."optaId" = h.opta_id
    WHERE (p."optaId" = '{clean_id}' OR p.PLAYER_NAME ILIKE '%{player_name}%')
      AND p.MATCH_DATE >= '2025-07-01'
    ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side(dp=None):
    # ... (Din eksisterende kode for hold/spiller valg og t_pitch tab)

    # --- TAB: FYSISK DATA (OPDATERET MED TIP/OTIP) ---
    with t_phys:
        df_phys = get_advanced_physical_data(valgt_spiller, valgt_player_uuid, conn)
        
        if df_phys is not None and not df_phys.empty:
            latest = df_phys.iloc[0]
            
            # Top Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
            m1.caption(f"TIP: {round(latest['DISTANCE_TIP']/1000, 1)} | OTIP: {round(latest['DISTANCE_OTIP']/1000, 1)}")
            
            m2.metric("HSR Meter", f"{int(latest['DISTANCE_HSR'])} m")
            m3.metric("Topfart", f"{round(latest['TOP_SPEED'], 1)} km/t")
            m4.metric("HI Runs (T/M/O)", f"{int(latest['HI_RUNS_TOTAL'])}", 
                      help=f"TIP: {latest['HI_RUNS_TIP']} | OTIP: {latest['HI_RUNS_OTIP']}")

            st.markdown("---")
            
            # Grafer og Analyse
            c_left, c_right = st.columns([1.2, 1])
            
            with c_left:
                st.subheader("Sæsonudvikling")
                # Din eksisterende bar-chart logik her...
                # (Brug df_phys til at lave graferne som i din forrige kode)
            
            with c_right:
                st.subheader("Besiddelses-kontekst (Seneste kamp)")
                # Donut chart for TIP/OTIP/BOP
                labels = ['Med bold (TIP)', 'Mod bold (OTIP)', 'Bold ude (BOP)']
                values = [latest['DISTANCE_TIP'], latest['DISTANCE_OTIP'], latest['DISTANCE_BOP']]
                
                fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, 
                                               marker_colors=['#2ecc71', '#e74c3c', '#95a5a6'])])
                fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300, showlegend=True)
                st.plotly_chart(fig_pie, use_container_width=True)

            # Intensitetszoner i bunden
            st.subheader("Intensitetsfordeling (m)")
            zones = ['Walking', 'Jogging', 'Running', 'HSR', 'Sprinting']
            z_vals = [latest['WALKING'], latest['JOGGING'], latest['RUNNING'], latest['DISTANCE_HSR'], latest['DISTANCE_SPRINT']]
            fig_z = px.bar(x=zones, y=z_vals, labels={'x':'Zone', 'y':'Meter'}, color_discrete_sequence=['#cc0000'])
            fig_z.update_layout(plot_bgcolor='white', height=300)
            st.plotly_chart(fig_z, use_container_width=True)

        else:
            st.info("Ingen Second Spectrum data fundet for denne spiller.")
