import streamlit as st
import pandas as pd

def vis_side(session, valgt_hold_navn):
    """
    Denne funktion kaldes af din hoved-app.
    Den håndterer mapping, SQL-kald og visning af Top 5 fysiske spillere.
    """
    
    # 1. Konfiguration af hold (Tilføj selv flere efter behov)
    # Det er vigtigt at forkortelsen matcher det, der står i MATCH_TEAMS i SS
    TEAM_CONFIG = {
        "Hvidovre": {"wyid": 7490, "abbr": "HVI"},
        "Kolding IF": {"wyid": 3538, "abbr": "KIF"},
        "FC Fredericia": {"wyid": 3527, "abbr": "FCF"},
        "B93": {"wyid": 3531, "abbr": "B93"},
        "AC Horsens": {"wyid": 3524, "abbr": "ACH"},
        "Esbjerg fB": {"wyid": 3528, "abbr": "EFB"},
        "Hillerød": {"wyid": 3535, "abbr": "HIL"},
        "Hobro": {"wyid": 3533, "abbr": "HOB"},
        "OB": {"wyid": 331, "abbr": "OB"},
        "Roskilde": {"wyid": 3529, "abbr": "RBF"},
        "Vendsyssel": {"wyid": 3526, "abbr": "VFF"}
    }

    config = TEAM_CONFIG.get(valgt_hold_navn)

    if not config:
        st.warning(f"Konfiguration for {valgt_hold_navn} ikke fundet. Tilføj WYID og Abbr i TEAM_CONFIG.")
        return

    st.subheader(f"Top 5: Fysiske Profiler - {valgt_hold_navn}")

    # 2. Den SQL logik vi ved virker (Wyscout-trup som filter)
    query = f"""
    WITH TEAM_TRUP AS (
        SELECT 
            (TRIM(FIRSTNAME) || ' ' || TRIM(LASTNAME)) as FULL_NAME,
            SHORTNAME,
            MAX(IMAGEDATAURL) as IMG_URL
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS 
        WHERE CURRENTTEAM_WYID = {config['wyid']}
        GROUP BY 1, 2
    ),
    SS_PHYSICAL AS (
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

    try:
        df = session.sql(query).to_pandas()

        if not df.empty:
            max_dist = df['DIST'].max()

            for _, row in df.iterrows():
                # Formatering af data
                dist_km = row['DIST'] / 1000
                bar_width = (row['DIST'] / max_dist) * 100
                
                # Visuel række
                col1, col2 = st.columns([1, 4])
                
                with col1:
                    img = row['IMAGE_URL']
                    if "ndplayer" in img:
                        img = "https://via.placeholder.com/150"
                    st.image(img, width=90)
                
                with col2:
                    st.markdown(f"**{row['FULL_NAME']}**")
                    # Dynamisk bar-graf
                    st.markdown(f"""
                        <div style="background:#333; width:100%; height:12px; border-radius:5px; margin: 5px 0;">
                            <div style="background:red; width:{bar_width}%; height:12px; border-radius:5px;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px; color: #aaa;">
                            <span>{dist_km:.2f} km Total</span>
                            <span>{int(row['HSR'])}m HSR</span>
                            <span>{row['SPEED']:.1f} km/t Max</span>
                        </div>
                    """, unsafe_allow_html=True)
                    st.write("---")
        else:
            st.info("Ingen fysiske data fundet for spillerne på dette hold.")

    except Exception as e:
        st.error(f"SQL Fejl: {e}")
