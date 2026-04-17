import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS

def vis_side():
    conn = _get_snowflake_conn()

    # --- 1. STYLING (Genskaber tabel-looket) ---
    st.markdown("""
        <style>
        .metric-row {
            display: flex;
            align-items: center;
            border-bottom: 1px solid #eee;
            padding: 5px 0;
        }
        .metric-name {
            width: 200px;
            font-weight: bold;
            font-size: 0.9rem;
            color: #333;
        }
        .player-col {
            flex: 1;
            text-align: center;
            padding: 0 5px;
        }
        .rank-box {
            border-radius: 4px;
            padding: 5px 0;
            font-weight: bold;
            font-size: 0.85rem;
            color: white;
        }
        /* Farvekoder baseret på rank (Grøn for top, rød for bund) */
        .rank-high { background-color: #00ff00; color: black; } /* Top 10% */
        .rank-mid { background-color: #90ee90; color: black; }  /* Top 30% */
        .rank-low { background-color: #ffcccb; color: black; }  /* Resten */
        
        .player-header-img {
            border-radius: 50%;
            object-fit: cover;
            margin-bottom: 5px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. HOLDVALG ---
    alle_hold = list(TEAMS.keys())
    valgt_navn = st.selectbox("Vælg hold:", alle_hold, index=alle_hold.index("Hvidovre") if "Hvidovre" in alle_hold else 0)
    target_wyid = TEAMS[valgt_navn]["team_wyid"]

    # --- 3. DATA (Vi henter flere metrics og beregner rank) ---
    query = f"""
    WITH STATS AS (
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST,
            AVG("HIGH SPEED RUNNING") as HSR,
            MAX(TOP_SPEED) as SPEED,
            AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        GROUP BY PLAYER_NAME
    ),
    RANKED AS (
        SELECT *,
            PERCENT_RANK() OVER (ORDER BY DIST DESC) as DIST_RANK,
            PERCENT_RANK() OVER (ORDER BY HSR DESC) as HSR_RANK,
            PERCENT_RANK() OVER (ORDER BY SPEED DESC) as SPEED_RANK,
            PERCENT_RANK() OVER (ORDER BY ACCELS DESC) as ACCELS_RANK
        FROM STATS
    ),
    TRUP AS (
        SELECT (FIRSTNAME || ' ' || LASTNAME) as FULL_NAME, SHORTNAME, IMAGEDATAURL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS
        WHERE CURRENTTEAM_WYID = {target_wyid}
    )
    SELECT r.*, t.IMAGEDATAURL 
    FROM RANKED r
    JOIN TRUP t ON (r.PLAYER_NAME = t.FULL_NAME OR r.PLAYER_NAME = t.SHORTNAME)
    ORDER BY r.DIST DESC LIMIT 5
    """

    try:
        df = pd.read_sql(query, conn)
        
        if not df.empty:
            # --- HEADER RÆKKE (Spiller billeder og navne) ---
            cols = st.columns([1.5, 1, 1, 1, 1, 1]) # 6 kolonner
            
            with cols[0]: st.write("") # Tom plads over metrics navne
            
            for i, (_, row) in enumerate(df.iterrows()):
                with cols[i+1]:
                    img = row['IMAGEDATAURL'] if row['IMAGEDATAURL'] else "https://via.placeholder.com/150"
                    st.markdown(f'<img src="{img}" class="player-header-img" width="60">', unsafe_allow_html=True)
                    st.markdown(f"**{row['PLAYER_NAME'].split()[-1]}**", help=row['PLAYER_NAME']) # Kun efternavn

            # --- METRIC RÆKKER ---
            metrics = [
                ("Distance Per 90", "DIST_RANK", "DIST"),
                ("Hi Distance Per 90", "HSR_RANK", "HSR"),
                ("Top Speed", "SPEED_RANK", "SPEED"),
                ("Accelerations", "ACCELS_RANK", "ACCELS")
            ]

            for label, rank_col, val_col in metrics:
                st.markdown("---")
                m_cols = st.columns([1.5, 1, 1, 1, 1, 1])
                with m_cols[0]:
                    st.markdown(f"**{label}**")
                
                for i, (_, row) in enumerate(df.iterrows()):
                    rank_val = row[rank_col]
                    # Bestem farveklasse baseret på rank
                    color_class = "rank-high" if rank_val <= 0.1 else "rank-mid" if rank_val <= 0.3 else "rank-low"
                    
                    with m_cols[i+1]:
                        # Viser rank som "1st", "2nd" osv (simuleret her)
                        rank_text = f"{int(rank_val * 100)}%" 
                        st.markdown(f'<div class="rank-box {color_class}">{rank_text}</div>', unsafe_allow_html=True)

        else:
            st.info("Ingen data fundet.")
    except Exception as e:
        st.error(f"Fejl: {e}")
