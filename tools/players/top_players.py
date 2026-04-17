import streamlit as st
import pandas as pd

# --- KONFIGURATION (Hvidovre-specifik) ---
TARGET_WYID = 7490
# Vi bruger en fleksibel navne-søgning i SQL i stedet for de lange SSIID-strenge, 
# da vi nu har lært, at MATCH_TEAMS i din tabel indeholder 'HVI'
TEAM_SEARCH_TERM = '%HVI%' 

def get_top_5_physical_data(session):
    # SQL Query der forener Wyscout (Truppen) med Second Spectrum (Fysisk data)
    query = f"""
    WITH HVI_TRUP AS (
        -- 1. Definer Hvidovres nuværende trup fra Wyscout (Vores Facitliste)
        SELECT 
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
            SHORTNAME,
            PLAYER_WYID,
            MAX(IMAGEDATAURL) as IMG_URL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
        WHERE CURRENTTEAM_WYID = {TARGET_WYID}
        GROUP BY 1, 2, 3
    ),
    SS_PHYSICAL AS (
        -- 2. Hent fysisk gennemsnit for alle spillere i sæsonen
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST, 
            AVG("HIGH SPEED RUNNING") as HSR, 
            MAX(TOP_SPEED) as SPEED, 
            AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        AND MATCH_TEAMS LIKE '{TEAM_SEARCH_TERM}'
        GROUP BY PLAYER_NAME
    )
    -- 3. Kobbel dem sammen via navne-match
    SELECT 
        w.FULL_NAME,
        s.DIST,
        s.HSR,
        s.SPEED,
        s.ACCELS,
        COALESCE(w.IMG_URL, 'https://via.placeholder.com/150') as IMAGE_URL
    FROM HVI_TRUP w
    INNER JOIN SS_PHYSICAL s ON (
        s.PLAYER_NAME = w.FULL_NAME 
        OR s.PLAYER_NAME = w.SHORTNAME
        OR w.FULL_NAME LIKE '%' || s.PLAYER_NAME || '%'
        OR s.PLAYER_NAME LIKE '%' || w.SHORTNAME || '%'
    )
    ORDER BY s.DIST DESC 
    LIMIT 5
    """
    return session.sql(query).to_pandas()

# --- STREAMLIT UI ---
st.set_page_config(layout="wide")
st.title("Top 5: Løbestærke Spillere (Hvidovre IF)")

# Antager du har en aktiv Snowflake-session i din app
try:
    df = get_top_5_physical_data(session)

    if not df.empty:
        # Find højeste distance for at kunne skalere de røde bars (0-100%)
        max_dist = df['DIST'].max()

        # Styling af containeren
        st.markdown("""
            <style>
            .player-row { margin-bottom: 25px; align-items: center; }
            .bar-container { background-color: #333; border-radius: 4px; height: 12px; width: 100%; margin: 5px 0; }
            .bar-fill { background-color: #FF0000; height: 12px; border-radius: 4px; }
            .stat-text { font-size: 13px; color: #CCCCCC; display: flex; justify-content: space-between; }
            </style>
        """, unsafe_allow_html=True)

        for index, row in df.iterrows():
            # Beregn værdier
            dist_km = row['DIST'] / 1000
            hsr_m = int(row['HSR'])
            speed_kmh = round(row['SPEED'], 1)
            bar_width = (row['DIST'] / max_dist) * 100

            # Layout med to kolonner
            col_img, col_data = st.columns([1, 6])

            with col_img:
                # Håndtering af Wyscout standard-ikoner (ndplayer)
                img_url = row['IMAGE_URL']
                if "ndplayer" in img_url:
                    # Vis klublogo eller placeholder hvis spillerfoto mangler
                    st.image("https://via.placeholder.com/150", width=90)
                else:
                    st.image(img_url, width=90)

            with col_data:
                st.subheader(row['FULL_NAME'])
                
                # HTML Bar-graf
                st.markdown(f"""
                    <div class="bar-container">
                        <div class="bar-fill" style="width: {bar_width}%;"></div>
                    </div>
                    <div class="stat-text">
                        <span><strong>Distance:</strong> {dist_km:.2f} km</span>
                        <span><strong>HSR:</strong> {hsr_m} m</span>
                        <span><strong>Top Speed:</strong> {speed_kmh} km/t</span>
                        <span><strong>Accels:</strong> {int(row['ACCELS'])}</span>
                    </div>
                """, unsafe_allow_html=True)
                st.divider()

    else:
        st.info("Kunne ikke finde fysiske data for spillerne i denne periode.")

except Exception as e:
    st.error(f"Der opstod en fejl ved hentning af data: {e}")
