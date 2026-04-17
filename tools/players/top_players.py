import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
# Importér din mapping-fil
from data.utils.team_mapping import TEAMS

def vis_side():
    # 1. Opret forbindelse
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # 2. Holdvælger baseret på din TEAMS mapping (kun 1. Division)
    liga_hold = [name for name, info in TEAMS.items() if info.get("league") == "1. Division"]
    
    # Sørg for at Hvidovre er valgt som standard
    default_idx = liga_hold.index("Hvidovre") if "Hvidovre" in liga_hold else 0
    valgt_navn = st.selectbox("Vælg hold (1. Division):", liga_hold, index=default_idx)
    
    # Hent IDs fra din mapping
    team_info = TEAMS[valgt_navn]
    wyid = team_info["team_wyid"]
    logo_url = team_info["logo"]

    # 3. SQL: Vi bruger nu det præcise team_wyid fra din mapping
    # Det fjerner problemet med at navne som "Kolding" vs "Kolding IF" ikke matcher
    query = f"""
    WITH SPILLERE AS (
        SELECT 
            SHORTNAME, 
            IMAGEDATAURL as PLAYER_IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = {wyid}
    )
    SELECT 
        s.PLAYER_NAME,
        AVG(s.DISTANCE) as DIST, 
        AVG(s."HIGH SPEED RUNNING") as HSR, 
        MAX(s.TOP_SPEED) as SPEED,
        MAX(sp.PLAYER_IMG) as IMG
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
    JOIN SPILLERE sp ON s.PLAYER_NAME = sp.SHORTNAME
    WHERE s.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
    GROUP BY s.PLAYER_NAME
    ORDER BY DIST DESC
    LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)

        # Vi overskriver kolonnenavne til UPPERCASE for at være sikre
        df.columns = [x.upper() for x in df.columns]

        # Overskrift og logo
        st.write("---")
        col_l, col_t = st.columns([1, 6])
        with col_l:
            st.image(logo_url, width=80)
        with col_t:
            st.subheader(f"Top 5: Fysiske Profiler ({valgt_navn})")

        if not df.empty:
            max_dist = df['DIST'].max()

            for _, row in df.iterrows():
                c1, c2 = st.columns([1, 5])
                with c1:
                    # Tjek for billede, ellers placeholder
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
                    st.image(img, width=70)
                with c2:
                    st.markdown(f"**{row['PLAYER_NAME']}**")
                    
                    # Bar-visualisering
                    bredde = (row['DIST'] / max_dist) * 100
                    st.markdown(f"""
                        <div style="background:#222; width:100%; height:10px; border-radius:5px; margin: 5px 0;">
                            <div style="background:#df003b; width:{bredde}%; height:10px; border-radius:5px;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    dist_km = row['DIST'] / 1000
                    st.caption(f"{dist_km:.2f} km gns. | {int(row['HSR'])}m HSR | {row['SPEED']} km/t max")
                    st.write("")
        else:
            st.info(f"Ingen fysiske data fundet for {valgt_navn} i databasen.")

    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")
