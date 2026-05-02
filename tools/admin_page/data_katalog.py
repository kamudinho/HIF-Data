import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from mplsoccer import Pitch, VerticalPitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO

def vis_side(conn):
    st.write("### 🛠 Datakatalog & Kolonneoversigt")
    
    # Header information i din faste stil
    st.info(f"Bruger: {st.session_state.get('user')}")
    st.info(f"Rolle: Admin") 
    st.info(f"Sæson: 2025/2026") # NordicBet Liga (328)

    # Liste over relevante tabeller
    tabeller = ['OPTA_MATCHEXPECTEDGOALS', 'OPTA_MATCHSTATS', 'OPTA_PLAYERS']
    valgt_tabel = st.selectbox("Vælg tabel for at se tilgængelige kolonner:", tabeller)

    if valgt_tabel:
        st.write(f"#### Kolonner i {valgt_tabel}")
        
        # SQL til at hente metadata fra INFORMATION_SCHEMA
        query_cols = f"""
            SELECT COLUMN_NAME, DATA_TYPE 
            FROM KLUB_HVIDOVREIF.INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{valgt_tabel}' 
            AND TABLE_SCHEMA = 'AXIS'
            ORDER BY ORDINAL_POSITION
        """
        
        try:
            # Da vi bruger en manuel connector, bruger vi pandas til at læse SQL'en
            df_cols = pd.read_sql(query_cols, conn)
            st.dataframe(df_cols, use_container_width=True, hide_index=True)
            
            # Hvis det er en stat-tabel, viser vi de unikke STAT_TYPEs (f.eks. xG, xA)
            if "STATS" in valgt_tabel or "EXPECTED" in valgt_tabel:
                st.write("#### Underliggende data (STAT_TYPE)")
                
                # Vi filtrerer på din aktuelle sæson for at gøre oversigten relevant
                query_stats = f"""
                    SELECT DISTINCT STAT_TYPE 
                    FROM KLUB_HVIDOVREIF.AXIS.{valgt_tabel} 
                    WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'
                    LIMIT 100
                """
                df_stats = pd.read_sql(query_stats, conn)
                st.dataframe(df_stats, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"Kunne ikke hente kolonner: {e}")
            st.warning("Dette skyldes ofte manglende USAGE-rettigheder på INFORMATION_SCHEMA for din rolle.")
