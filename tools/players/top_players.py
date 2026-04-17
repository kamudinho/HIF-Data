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

    # --- HOLDVÆLGER BASERET PÅ KONFIGURATION ---
    # Vi bruger turnering ID 328 (NordicBet Liga) som defineret i din konfiguration
    comp_id = 328 
    
    try:
        # Vi henter holdnavne der er tilknyttet den specifikke turnering
        # Dette sikrer at vi kun ser hold fra 1. division
        hold_liste_query = f"""
            SELECT DISTINCT TEAMNAME 
            FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS 
            WHERE COMPETITION_WYID = {comp_id}
            ORDER BY TEAMNAME
        """
        hold_df = pd.read_sql(hold_liste_query, conn)
        hold_navne = hold_df['TEAMNAME'].tolist()
        
        if not hold_navne:
            hold_navne = ["Hvidovre"] # Fallback

        # Selectbox til valg af hold
        default_idx = hold_navne.index('Hvidovre') if 'Hvidovre' in hold_navne else 0
        valgt_hold = st.selectbox("Vælg hold (NordicBet Liga):", hold_navne, index=default_idx)
        st.session_state["valgt_hold"] = valgt_hold
        
    except Exception as e:
        st.warning(f"Kunne ikke hente holdlisten via turnering ID: {e}")
        valgt_hold = st.session_state.get("valgt_hold", "Hvidovre")

    # 2. SQL Logik til Top 5
    safe_hold = valgt_hold.replace("'", "''")

    query = f"""
    WITH HOLD AS (
        SELECT TEAM_WYID, IMAGEDATAURL as TEAM_LOGO
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS
        WHERE TEAMNAME = '{safe_hold}'
        AND COMPETITION_WYID = {comp_id}
        LIMIT 1
    ),
    SPILLERE AS (
        SELECT 
            SHORTNAME, 
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
    JOIN SPILLERE sp ON s.PLAYER_NAME = sp.SHORTNAME
    WHERE s.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
    GROUP BY s.PLAYER_NAME
    ORDER BY DIST DESC
    LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)

        if not df.empty:
            df.columns = [x.upper() for x in df.columns]

            st.write("---")
            col_l, col_t = st.columns([1, 6])
            with col_l:
                logo = df['LOGO'].iloc[0]
                if logo:
                    st.image(logo, width=80)
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
