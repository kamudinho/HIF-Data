import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    conn = _get_snowflake_conn()

    # --- 1. STYLING (Genskaber looket fra billedet) ---
    st.markdown("""
        <style>
        .player-card {
            background-color: transparent;
            padding: 10px 0px;
            border-bottom: 1px solid #333;
        }
        .player-name {
            font-weight: bold;
            font-size: 1.1rem;
            margin-bottom: 5px;
        }
        .custom-bar-container {
            background-color: #333;
            border-radius: 10px;
            width: 100%;
            height: 8px;
            margin: 8px 0;
        }
        .custom-bar-fill {
            background-color: #df003b; /* Den røde fra billedet */
            height: 100%;
            border-radius: 10px;
        }
        .stat-text {
            color: #999;
            font-size: 0.85rem;
        }
        img.player-img {
            border-radius: 50%; /* Gør billederne runde som på dit screenshot */
            object-fit: cover;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. HOLDVALG ---
    alle_hold = list(TEAMS.keys())
    col_header, _ = st.columns([2, 2])
    with col_header:
        valgt_navn = st.selectbox("Vælg hold:", alle_hold, index=alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0)
    
    team_info = TEAMS[valgt_navn]
    target_wyid = team_info["team_wyid"]
    logo_url = team_info["logo"]

    # --- 3. DATA HENTNING (Din optimerede SQL) ---
    query = f"""
    WITH TRUP AS (
        SELECT 
            (TRIM(w.FIRSTNAME) || ' ' || TRIM(w.LASTNAME)) as FULL_NAME,
            w.SHORTNAME,
            MAX(w.IMAGEDATAURL) as IMG_URL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS w
        WHERE w.CURRENTTEAM_WYID = {target_wyid}
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
        w.FULL_NAME, s.DIST, s.HSR, s.SPEED,
        COALESCE(w.IMG_URL, 'https://via.placeholder.com/150') as IMG
    FROM TRUP w
    INNER JOIN SS_PHYSICAL s ON (
        s.PLAYER_NAME = w.FULL_NAME OR s.PLAYER_NAME = w.SHORTNAME
        OR w.FULL_NAME LIKE '%' || s.PLAYER_NAME || '%'
    )
    ORDER BY s.DIST DESC LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)
        df.columns = [x.upper() for x in df.columns]

        if not df.empty:
            # Overskrift med Logo
            st.write("---")
            c1, c2 = st.columns([1, 8])
            with c1: st.image(logo_url, width=60)
            with c2: st.subheader(f"Top 5: Fysiske Profiler | {valgt_navn}")

            max_dist = df['DIST'].max()

            # --- 4. RENDER PLAYERS (Genskabelsen af billedet) ---
            for _, row in df.iterrows():
                # Beregn procent til baren
                procent = (row['DIST'] / max_dist) * 100
                
                # Container for hver spiller
                with st.container():
                    col_img, col_data = st.columns([1, 6])
                    
                    with col_img:
                        # Vi bruger HTML for at få det runde billede præcis som på screenshot
                        st.markdown(f'<img src="{row["IMG"]}" class="player-img" width="70" height="70">', unsafe_allow_html=True)
                    
                    with col_data:
                        st.markdown(f'<div class="player-name">{row["FULL_NAME"]}</div>', unsafe_allow_html=True)
                        
                        # Den røde bar
                        st.markdown(f"""
                            <div class="custom-bar-container">
                                <div class="custom-bar-fill" style="width: {procent}%;"></div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Stats tekst
                        km = row['DIST'] / 1000
                        st.markdown(f"""
                            <div class="stat-text">
                                {km:.2f} km gns. | {int(row['HSR'])}m HSR | {row['SPEED']} km/t max
                            </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown('<div style="margin-bottom:20px;"></div>', unsafe_allow_html=True)
        else:
            st.info("Ingen data fundet for dette hold.")

    except Exception as e:
        st.error(f"Fejl: {e}")
