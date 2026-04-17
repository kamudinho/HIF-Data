import streamlit as st

# 1. Mapping af hold (SSIID, Wyscout ID og SS-Forkortelse)
# Tilføj selv de resterende hold her
TEAM_CONFIG = {
    "Hvidovre": {"wyid": 7490, "abbr": "HVI"},
    "Kolding IF": {"wyid": 3538, "abbr": "KIF"}, # Eksempel ID
    "FC Fredericia": {"wyid": 3527, "abbr": "FCF"}, # Eksempel ID
    # Fortsæt listen...
}

def get_top_5_universal(session, hold_navn):
    config = TEAM_CONFIG.get(hold_navn)
    if not config:
        return None

    query = f"""
    WITH TEAM_TRUP AS (
        -- Henter spillere for det valgte hold fra Wyscout
        SELECT 
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
            SHORTNAME,
            MAX(IMAGEDATAURL) as IMG_URL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
        WHERE CURRENTTEAM_WYID = {config['wyid']}
        GROUP BY 1, 2
    ),
    SS_PHYSICAL AS (
        -- Henter fysisk data kun for kampe hvor holdets forkortelse optræder
        SELECT 
            PLAYER_NAME,
            AVG(DISTANCE) as DIST, 
            AVG("HIGH SPEED RUNNING") as HSR, 
            MAX(TOP_SPEED) as SPEED, 
            AVG(NO_OF_HIGH_INTENSITY_RUNS) as ACCELS
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS
        WHERE MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
        AND MATCH_TEAMS LIKE '%{config['abbr']}%'
        GROUP BY PLAYER_NAME
    )
    -- Matcher trup mod fysisk data
    SELECT 
        w.FULL_NAME,
        s.DIST, s.HSR, s.SPEED, s.ACCELS,
        COALESCE(w.IMG_URL, 'https://via.placeholder.com/150') as IMAGE_URL
    FROM TEAM_TRUP w
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

# --- APP LAYOUT ---
valgt_hold = st.selectbox("Vælg Hold", list(TEAM_CONFIG.keys()))

if st.button("Hent Top 5"):
    df = get_top_5_universal(session, valgt_hold)
    
    if df is not None and not df.empty:
        max_dist = df['DIST'].max()
        
        for _, row in df.iterrows():
            dist_km = row['DIST'] / 1000
            bar_width = (row['DIST'] / max_dist) * 100
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(row['IMAGE_URL'], width=80)
            with col2:
                st.markdown(f"**{row['FULL_NAME']}**")
                st.markdown(f"""
                    <div style="background:#333; width:100%; height:12px; border-radius:5px;">
                        <div style="background:red; width:{bar_width}%; height:12px; border-radius:5px;"></div>
                    </div>
                    <p style="font-size:12px;">{dist_km:.2f} km | {int(row['HSR'])}m HSR | {row['SPEED']:.1f} km/t</p>
                """, unsafe_allow_html=True)
    else:
        st.error("Ingen data fundet for dette hold.")
