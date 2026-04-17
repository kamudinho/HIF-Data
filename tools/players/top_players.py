import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def vis_side():
    """
    Finder holdet i WYSCOUT_TEAMS, derefter spillerne i WYSCOUT_PLAYERS,
    og kobler til sidst på Second Spectrum data via optaId.
    """
    
    # 1. Opret forbindelse
    try:
        session = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # 2. Hent det valgte hold fra din session_state
    # Hvis din variabel hedder noget andet end "valgt_hold", så ret navnet her.
    valgt_hold = st.session_state.get("valgt_hold", "Hvidovre")

    # 3. SQL: Den "rene" rækkefølge
    query = f"""
    WITH HOLD AS (
        -- Find holdet i WYSCOUT_TEAMS
        SELECT TEAM_WYID, IMAGEDATAURL as TEAM_LOGO
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS
        WHERE TEAMNAME = '{valgt_hold}'
        LIMIT 1
    ),
    SPILLERE AS (
        -- Find alle spillere for det hold i WYSCOUT_PLAYERS
        SELECT p.SHORTNAME, p.FULLNAME, p.OPTAID, p.IMAGEDATAURL as PLAYER_IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS p
        JOIN HOLD h ON p.CURRENTTEAM_WYID = h.TEAM_WYID
    )
    -- Kobbel på Second Spectrum Physical Summary
    SELECT 
        s.PLAYER_NAME,
        AVG(s.DISTANCE) as DIST, 
        AVG(s."HIGH SPEED RUNNING") as HSR, 
        MAX(s.TOP_SPEED) as SPEED,
        MAX(sp.PLAYER_IMG) as IMG,
        (SELECT TEAM_LOGO FROM HOLD) as LOGO
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
    JOIN SPILLERE sp ON s.optaId = sp.OPTAID
    WHERE s.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
    GROUP BY s.PLAYER_NAME
    ORDER BY DIST DESC
    LIMIT 5
    """

    try:
        df = session.sql(query).to_pandas()

        if not df.empty:
            # Layout: Logo og Overskrift
            col_l, col_t = st.columns([1, 6])
            with col_l:
                st.image(df['LOGO'].iloc[0], width=80)
            with col_t:
                st.subheader(f"Top 5: Fysiske Profiler ({valgt_hold})")

            max_dist = df['DIST'].max()

            # Vis de 5 spillere
            for _, row in df.iterrows():
                c1, c2 = st.columns([1, 5])
                with c1:
                    img = row['IMG'] if row['IMG'] else "https://via.placeholder.com/150"
                    st.image(img, width=70)
                with c2:
                    st.markdown(f"**{row['PLAYER_NAME']}**")
                    
                    # Rød bar baseret på distance
                    bredde = (row['DIST'] / max_dist) * 100
                    st.markdown(f"""
                        <div style="background:#222; width:100%; height:10px; border-radius:5px; margin: 5px 0;">
                            <div style="background:#df003b; width:{bredde}%; height:10px; border-radius:5px;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    dist_km = row['DIST'] / 1000
                    st.caption(f"{dist_km:.2f} km | {int(row['HSR'])}m HSR | {row['SPEED']} km/t")
                    st.write("")
        else:
            st.info(f"Ingen fysiske data fundet for {valgt_hold} i denne periode.")

    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")
