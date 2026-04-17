import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def vis_side():
    # 1. Opret forbindelse
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # 2. Hent valgt hold fra session_state
    valgt_hold = st.session_state.get("valgt_hold", "Hvidovre")
    safe_hold = valgt_hold.replace("'", "''")

    # 3. SQL: Præcis rækkefølge
    query = f"""
    WITH HOLD AS (
        SELECT TEAM_WYID, IMAGEDATAURL as TEAM_LOGO
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS
        WHERE TEAMNAME = '{safe_hold}'
        LIMIT 1
    ),
    SPILLERE AS (
        SELECT 
            OPTAID, 
            IMAGEDATAURL as PLAYER_IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = (SELECT TEAM_WYID FROM HOLD)
    )
    SELECT 
        s.PLAYER_NAME,
        AVG(s.DISTANCE) as DIST, 
        AVG(s."HIGH SPEED RUNNING") as HSR, 
        MAX(s.TOP_SPEED) as SPEED,
        MAX(sp.PLAYER_IMG) as IMG,
        (SELECT TEAM_LOGO FROM HOLD) as LOGO
    FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS s
    JOIN SPILLERE sp ON s."optaId" = sp.OPTAID
    WHERE s.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
    GROUP BY s.PLAYER_NAME
    ORDER BY DIST DESC
    LIMIT 5
    """

    try:
        # RETTELSE: Vi bruger pd.read_sql i stedet for session.sql
        df = pd.read_sql(query, conn)

        if not df.empty:
            # Layout: Logo og Overskrift
            col_l, col_t = st.columns([1, 6])
            with col_l:
                # Snowflake returnerer ofte kolonnenavne i UPPERCASE i Pandas
                logo_url = df['LOGO'].iloc[0]
                st.image(logo_url, width=80)
            with col_t:
                st.subheader(f"Top 5: Fysiske Profiler ({valgt_hold})")

            max_dist = df['DIST'].max()

            for _, row in df.iterrows():
                c1, c2 = st.columns([1, 5])
                with c1:
                    img = row['IMG'] if row['IMG'] and str(row['IMG']) != 'None' else "https://via.placeholder.com/150"
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
            st.info(f"Ingen fysiske data fundet for {valgt_hold}.")

    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")
