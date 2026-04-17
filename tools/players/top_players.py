import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS  # Din mapping fil

def vis_side():
    conn = _get_snowflake_conn()

    # --- 1. DROPDOWN BASERET PÅ DINE DATA ---
    # Vi henter alle holdnavne fra din TEAMS ordbog
    alle_hold = list(TEAMS.keys())
    
    col_sel, _ = st.columns([2, 2])
    with col_sel:
        # Hvidovre som default
        default_idx = alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0
        valgt_navn = st.selectbox("Vælg hold:", alle_hold, index=default_idx)

    # --- 2. HENT INFO FRA MAPPING ---
    # Nu har vi de præcise IDs og links uden at skulle spørge databasen
    team_data = TEAMS[valgt_navn]
    target_wyid = team_data["team_wyid"]
    logo_url = team_data["logo"]

    # --- 3. DYNAMISK SQL QUERY ---
    # Vi indsætter target_wyid direkte i din velfungerende query
    query = f"""
    WITH SELECTED_TRUP AS (
        SELECT 
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
            SHORTNAME,
            MAX(IMAGEDATAURL) as IMG_URL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
        WHERE CURRENTTEAM_WYID = {target_wyid}
        GROUP BY 1, 2
    ),
    SS_PHYSICAL AS (
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST, 
            AVG("HIGH SPEED RUNNING") as HSR, 
            MAX(TOP_SPEED) as SPEED
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        GROUP BY PLAYER_NAME
    )
    SELECT 
        w.FULL_NAME,
        s.DIST,
        s.HSR,
        s.SPEED,
        COALESCE(w.IMG_URL, 'https://via.placeholder.com/150') as FINAL_IMAGE_URL
    FROM SELECTED_TRUP w
    INNER JOIN SS_PHYSICAL s ON (
        s.PLAYER_NAME = w.FULL_NAME 
        OR s.PLAYER_NAME = w.SHORTNAME
        OR w.FULL_NAME LIKE '%' || s.PLAYER_NAME || '%'
        OR s.PLAYER_NAME LIKE '%' || w.SHORTNAME || '%'
    )
    ORDER BY s.DIST DESC 
    LIMIT 5
    """

    # --- 4. VISUALISERING ---
    try:
        df = pd.read_sql(query, conn)
        df.columns = [x.upper() for x in df.columns]

        if not df.empty:
            st.write("---")
            c_logo, c_text = st.columns([1, 6])
            with c_logo:
                st.image(logo_url, width=80)
            with c_text:
                st.subheader(f"Top 5: Fysiske Profiler | {valgt_navn}")

            max_dist = df['DIST'].max()

            for _, row in df.iterrows():
                p1, p2 = st.columns([1, 5])
                with p1:
                    st.image(row['FINAL_IMAGE_URL'], width=70)
                with p2:
                    st.markdown(f"**{row['FULL_NAME']}**")
                    procent = (row['DIST'] / max_dist) * 100
                    st.markdown(f"""
                        <div style="background:#333; width:100%; height:12px; border-radius:6px;">
                            <div style="background:#df003b; width:{procent}%; height:12px; border-radius:6px;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                    st.caption(f"{row['DIST']/1000:.2f} km | {int(row['HSR'])}m HSR | {row['SPEED']} km/t")
        else:
            st.info(f"Ingen kampdata fundet for {valgt_navn} (ID: {target_wyid}).")

    except Exception as e:
        st.error(f"Fejl: {e}")
