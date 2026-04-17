import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    # 1. Opret forbindelse
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # --- TRIN 1: HOLDVALG FRA MAPPING ---
    liga_hold = [name for name, info in TEAMS.items() if info.get("league") == "1. Division"]
    
    col_sel, _ = st.columns([2, 2])
    with col_sel:
        default_idx = liga_hold.index("Hvidovre") if "Hvidovre" in liga_hold else 0
        valgt_navn = st.selectbox("Vælg hold:", liga_hold, index=default_idx)
    
    team_info = TEAMS[valgt_navn]
    target_wyid = team_info["team_wyid"]
    logo_url = team_info["logo"]

    # --- TRIN 2 & 3: OPTA_PLAYERS -> SECOND SPECTRUM ---
    # Vi bruger OPTA_PLAYERS til at trække MATCH_NAME ud baseret på dit hold-ID
    query = f"""
    WITH SPILLERE_FRA_OPTA AS (
        -- Vi henter MATCH_NAME og billedet fra OPTA_PLAYERS (via WyScout ID kobling)
        SELECT 
            MATCH_NAME, 
            IMAGEDATAURL as PLAYER_IMG
        FROM KLUB_HVIDOVREIF.AXIS.OPTA_PLAYERS
        WHERE CURRENTTEAM_WYID = {target_wyid}
    )
    SELECT 
        s.PLAYER_NAME,
        AVG(s.DISTANCE) as DIST, 
        AVG(s."HIGH SPEED RUNNING") as HSR, 
        MAX(s.TOP_SPEED) as SPEED,
        MAX(sp.PLAYER_IMG) as IMG
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
    -- Her kobler vi Second Spectrum direkte på MATCH_NAME fra Opta
    JOIN SPILLERE_FRA_OPTA sp ON s.PLAYER_NAME = sp.MATCH_NAME
    WHERE s.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
    GROUP BY s.PLAYER_NAME
    ORDER BY DIST DESC
    LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)
        df.columns = [x.upper() for x in df.columns]

        if not df.empty:
            st.write("---")
            
            # Header
            c_logo, c_text = st.columns([1, 6])
            with c_logo:
                st.image(logo_url, width=80)
            with c_text:
                st.subheader(f"Top 5: Fysiske Profiler | {valgt_navn}")

            max_dist = df['DIST'].max()

            # Visning af de 5 mest løbestærke
            for _, row in df.iterrows():
                p1, p2 = st.columns([1, 5])
                with p1:
                    p_img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    st.image(p_img, width=70)
                with p2:
                    st.markdown(f"**{row['PLAYER_NAME']}**")
                    
                    # Bar visualisering i den rigtige røde farve
                    procent = (row['DIST'] / max_dist) * 100
                    st.markdown(f"""
                        <div style="background:#333; width:100%; height:12px; border-radius:6px;">
                            <div style="background:#df003b; width:{procent}%; height:12px; border-radius:6px;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    km = row['DIST'] / 1000
                    st.caption(f"{km:.2f} km gns. | {int(row['HSR'])}m HSR | {row['SPEED']} km/t max")
                    st.write("")
        else:
            st.warning(f"Ingen kampdata fundet i Second Spectrum for de spillere, der er registreret i Opta på {valgt_navn}.")

    except Exception as e:
        st.error(f"Fejl ved datahentning fra OPTA/SS: {e}")
