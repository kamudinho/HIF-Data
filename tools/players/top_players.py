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

    # --- NY HOLDVÆLGER SEKTION ---
    # Vi henter alle hold fra NordicBet Liga (328) for at fylde selectboxen
    try:
        hold_liste_query = """
            SELECT DISTINCT TEAMNAME 
            FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS 
            WHERE AREA_NAME = 'Denmark' 
            -- Du kan tilføje specifikt turneringstjek her hvis nødvendigt
            ORDER BY TEAMNAME
        """
        hold_df = pd.read_sql(hold_liste_query, conn)
        hold_navne = hold_df['TEAMNAME'].tolist()
        
        # Selectbox placeres øverst
        # Vi sætter default til 'Hvidovre' hvis det findes i listen
        default_index = hold_navne.index('Hvidovre') if 'Hvidovre' in hold_navne else 0
        valgt_hold = st.selectbox("Vælg hold fra ligaen:", hold_navne, index=default_index)
        
        # Vi gemmer valget i session_state, så andre sider også ved hvilket hold vi kigger på
        st.session_state["valgt_hold"] = valgt_hold
        
    except Exception as e:
        st.warning(f"Kunne ikke hente holdlisten: {e}")
        valgt_hold = st.session_state.get("valgt_hold", "Hvidovre")
    # -----------------------------

    safe_hold = valgt_hold.replace("'", "''")

    # 3. SQL: Navne-match inden for det valgte hold
    query = f"""
    WITH HOLD AS (
        SELECT TEAM_WYID, IMAGEDATAURL as TEAM_LOGO
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS
        WHERE TEAMNAME = '{safe_hold}'
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

            st.write("---") # Skillelinje efter vælgeren

            # Layout: Logo og Overskrift
            col_l, col_t = st.columns([1, 6])
            with col_l:
                logo_url = df['LOGO'].iloc[0]
                if logo_url:
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
            st.info(f"Ingen fysiske data fundet for {valgt_hold} i den valgte periode.")

    except Exception as e:
        st.error(f"Fejl ved datahentning: {e}")
