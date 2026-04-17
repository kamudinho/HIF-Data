import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # --- TOP BAR ---
    col1, col2 = st.columns([2, 2])
    with col1:
        valgt_navn = st.selectbox("Vælg hold:", list(TEAMS.keys()), key="sb_top5_final_v5")
        target_wyid = TEAMS[valgt_navn]["team_wyid"]
    with col2:
        mode = st.radio("Vælg data-visning:", ["Fysiske Data (P90)", "Tekniske Data (P90)"], horizontal=True, key="radio_top5_final_v5")

    # --- SQL (Standard uden besværlige SQL-filtre) ---
    if "Fysiske Data" in mode:
        query = f"""
        WITH LIGA_STATS AS (
            SELECT PLAYER_NAME, AVG(DISTANCE) as M1, AVG(RUNNING) as M2, AVG("HIGH SPEED RUNNING") as M3,
            AVG(SPRINTING) as M4, MAX(TOP_SPEED) as M5 FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
            WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30' GROUP BY 1
        ),
        LIGA_RANKED AS (
            SELECT *, RANK() OVER (ORDER BY M1 DESC) as M1_RANK, RANK() OVER (ORDER BY M2 DESC) as M2_RANK,
            RANK() OVER (ORDER BY M3 DESC) as M3_RANK, RANK() OVER (ORDER BY M4 DESC) as M4_RANK,
            RANK() OVER (ORDER BY M5 DESC) as M5_RANK FROM LIGA_STATS
        ),
        VALGT_TRUP AS (
            SELECT (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME, MAX(IMAGEDATAURL) as IMG
            FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS WHERE CURRENTTEAM_WYID = {target_wyid} GROUP BY 1
        )
        SELECT t.IMG, t.FULL_NAME as WYS_NAME, r.* FROM VALGT_TRUP t
        INNER JOIN LIGA_RANKED r ON (t.FULL_NAME LIKE '%' || r.PLAYER_NAME || '%' OR r.PLAYER_NAME LIKE '%' || t.FULL_NAME || '%')
        """
        metrics = [("Total Dist.", "M1_RANK", "M1"), ("Running", "M2_RANK", "M2")]
    else:
        # (Tilsvarende for Tekniske Data...)
        query = "..." 

    try:
        df = pd.read_sql(query, conn)
        
        # --- PYTHON FIREWALL (Dette fjerner dem med 100% sikkerhed) ---
        if valgt_navn == "Kolding IF":
            # Vi fjerner alle rækker hvor navnet indeholder Enemark eller Westh
            df = df[~df['WYS_NAME'].str.contains('Enemark|Westh', case=False, na=False)]
        
        if not df.empty:
            df = df.sort_values("M1_RANK").head(5)
            
            # --- RENDER LOGIK (Billeder og Bars) ---
            st.write("---")
            cols = st.columns([2.5, 1, 1, 1, 1, 1])
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://cdn.wyscout.com/photos/players/public/ndplayer_100x130.png"
                    st.markdown(f'<div style="text-align:center"><img src="{img}" style="border-radius:50%" width="65"><br><small><b>{row["WYS_NAME"].split()[-1]}</b></small></div>', unsafe_allow_html=True)
            
            # (Resten af dine bars her...)
    except Exception as e:
        st.error(f"Fejl: {e}")

vis_side()
