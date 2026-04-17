import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn

def vis_side():
    """
    Henter Top 5 mest løbestærke spillere for det valgte hold.
    Følger rækkefølgen: WyScout_Teams -> WyScout_Players -> Second Spectrum Stats.
    """
    
    # 1. Opret forbindelse til Snowflake
    try:
        conn = _get_snowflake_conn()
    except Exception as e:
        st.error(f"Forbindelsesfejl: {e}")
        return

    # 2. Hent valgt hold fra session_state
    valgt_hold = st.session_state.get("valgt_hold", "Hvidovre")
    # Sikrer mod fejl hvis holdnavnet indeholder en apostrof (fx B.93')
    safe_hold = valgt_hold.replace("'", "''")

    # 3. SQL Query med din optimerede CTE-struktur
    query = f"""
    WITH HOLD AS (
        -- Find holdet og logo i WYSCOUT_TEAMS
        SELECT TEAM_WYID, IMAGEDATAURL as TEAM_LOGO
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS
        WHERE TEAMNAME = '{safe_hold}'
        LIMIT 1
    ),
    SPILLERE AS (
        -- Find alle spillere for holdet i WYSCOUT_PLAYERS
        SELECT 
            OPTAID, 
            IMAGEDATAURL as PLAYER_IMG
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = (SELECT TEAM_WYID FROM HOLD)
    )
    -- Hent fysisk data og kobl på spillere via OptaID
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
        # Hent data ind i Pandas
        df = pd.read_sql(query, conn)

        st.write(f"Søger efter hold: {valgt_hold}")
        st.write(f"Antal rækker fundet: {len(df)}")
        if not df.empty:
            st.write(df.head()) # Vis de første par rækker

        if not df.empty:
            # Tving alle kolonnenavne til UPPERCASE for at undgå KeyError
            df.columns = [x.upper() for x in df.columns]

            # Layout: Logo og Overskrift
            col_l, col_t = st.columns([1, 6])
            with col_l:
                logo_url = df['LOGO'].iloc[0]
                st.image(logo_url, width=80)
            with col_t:
                st.subheader(f"Top 5: Fysiske Profiler ({valgt_hold})")

            # Find max distance til skalering af bars
            max_dist = df['DIST'].max()

            st.write("---")

            # Loop gennem de 5 spillere
            for _, row in df.iterrows():
                c1, c2 = st.columns([1, 5])
                
                with c1:
                    # Vis spillerbillede (eller placeholder hvis det mangler)
                    img_path = row['IMG']
                    if not img_path or str(img_path) == 'None' or "ndplayer" in str(img_path):
                        img_path = "https://via.placeholder.com/150"
                    st.image(img_path, width=75)
                
                with c2:
                    st.markdown(f"**{row['PLAYER_NAME']}**")
                    
                    # Beregn bar-bredde
                    bredde = (row['DIST'] / max_dist) * 100
                    
                    # Rød progress bar (Hvidovre stil)
                    st.markdown(f"""
                        <div style="background:#262626; width:100%; height:12px; border-radius:6px; margin: 8px 0;">
                            <div style="background:#df003b; width:{bredde}%; height:12px; border-radius:6px;"></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Stats i bunden
                    dist_km = row['DIST'] / 1000
                    st.caption(f"🏃 {dist_km:.2f} km gns.  |  ⚡ {int(row['HSR'])}m HSR  |  🚀 {row['SPEED']} km/t max")
                    st.write("") # Ekstra luft mellem spillere

        else:
            st.info(f"Der blev ikke fundet nogle fysiske kampdata for {valgt_hold} i denne periode.")

    except Exception as e:
        st.error(f"Der skete en fejl ved behandling af data: {e}")
