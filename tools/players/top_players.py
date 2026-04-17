import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    # 1. Forbindelse
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # 2. Holdvælger (Baseret på din mapping-fil)
    # Vi tager alle hold der er markeret som '1. Division'
    liga_hold = [name for name, info in TEAMS.items() if info.get("league") == "1. Division"]
    
    col_sel, col_empty = st.columns([2, 2])
    with col_sel:
        default_idx = liga_hold.index("Hvidovre") if "Hvidovre" in liga_hold else 0
        valgt_navn = st.selectbox("Vælg hold:", liga_hold, index=default_idx)
    
    # Hent data fra din TEAMS dictionary
    team_info = TEAMS[valgt_navn]
    target_wyid = team_info["team_wyid"]
    logo_url = team_info["logo"]

    # 3. SQL: Brug TEAM_WYID til at finde de korrekte spillere
    query = f"""
    WITH SPILLERE AS (
        -- Her isolerer vi truppen via det unikke ID
        SELECT 
            SHORTNAME, 
            IMAGEDATAURL as PLAYER_IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = {target_wyid}
    )
    SELECT 
        s.PLAYER_NAME,
        AVG(s.DISTANCE) as DIST, 
        AVG(s."HIGH SPEED RUNNING") as HSR, 
        MAX(s.TOP_SPEED) as SPEED,
        MAX(sp.PLAYER_IMG) as IMG
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
    -- Match på navn, men KUN for de spillere vi lige har fundet via TEAM_WYID
    JOIN SPILLERE sp ON s.PLAYER_NAME = sp.SHORTNAME
    WHERE s.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
    GROUP BY s.PLAYER_NAME
    ORDER BY DIST DESC
    LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)

        if not df.empty:
            # Sikr kolonnenavne (Pandas/Snowflake uppercase standard)
            df.columns = [x.upper() for x in df.columns]

            st.write("---")
            
            # Header med logo fra din mapping
            c_logo, c_text = st.columns([1, 6])
            with c_logo:
                st.image(logo_url, width=80)
            with c_text:
                st.subheader(f"Top 5: Fysiske Profiler | {valgt_navn}")

            max_dist = df['DIST'].max()

            # Vis spillere
            for _, row in df.iterrows():
                p1, p2 = st.columns([1, 5])
                with p1:
                    # Tjek om billedet findes, ellers brug placeholder
                    p_img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    st.image(p_img, width=70)
                with p2:
                    st.markdown(f"**{row['PLAYER_NAME']}**")
                    
                    # Bar progress
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
            st.warning(f"Ingen kampdata fundet for {valgt_navn} (WYID: {target_wyid}) i den valgte periode.")

    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")
