import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})
    valgt_liga_global = dp.get("VALGT_LIGA", "1. division")

    # --- CSS ---
    hif_rod = "#df003b"
    st.markdown(f"""
        <style>
        .stat-box {{ text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }}
        .stat-label {{ font-size: 10px; color: gray; text-transform: uppercase; }}
        .stat-val {{ font-weight: bold; font-size: 14px; }}
        .form-container {{ display: flex; gap: 4px; margin-top: 4px; }}
        .form-dot {{ 
            display: flex; align-items: center; justify-content: center; 
            width: 24px; height: 24px; border-radius: 3px; 
            color: white; font-size: 11px; font-weight: bold; 
            cursor: help;
        }}
        .win {{ background-color: #28a745; }} 
        .draw {{ background-color: #ffc107; }} 
        .loss {{ background-color: #dc3545; }}
        .date-header {{ background: #eee; padding: 5px 15px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #444; border-left: 4px solid {hif_rod}; }}
        .score-pill {{ background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; min-width: 70px; display: inline-block; text-align: center; }}
        .time-pill {{ background: #f0f2f6; color: #333; border-radius: 4px; padding: 2px 10px; font-size: 0.9rem; min-width: 70px; display: inline-block; text-align: center; }}
        </style>
    """, unsafe_allow_html=True)

   # --- 1. TOP BAR (Dropdown + Stats på samme linje) ---
    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])

    with top_cols[0]:
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    # Tegn stats i top_cols
    stats_list = [("K", stats["K"]), ("S", stats["S"]), ("U", stats["U"]), ("N", stats["N"]), ("M+", stats["M+"]), ("M-", stats["M-"]), ("+/-", stats["M+"]-stats["M-"])]
    for i, (l, v) in enumerate(stats_list):
        with top_cols[i+1]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- 2. TABS OG FORM-BAROMETER PÅ SAMME LINJE ---
    # Vi laver to kolonner: en bred til tabs og en smal til form
    tab_col, form_col = st.columns([5, 1])

    with tab_col:
        tab_played, tab_fixtures = st.tabs(["Resultater", "Kommende kampe"])

    with form_col:
        # Vi tilføjer lidt margin-top for at flugte med tabs-teksten
        form_html = "".join([f"<span class='form-dot {f['res']}' title='{f['hover']}'>{f['txt']}</span>" for f in stats["form"][-5:]])
        st.markdown(f"""
            <div style='display: flex; justify-content: flex-end; margin-top: 12px;'>
                <div class='form-container'>{form_html}</div>
            </div>
        """, unsafe_allow_html=True)

    # --- 3. INDHOLD I TABS ---
    # (Her bruger vi din tegn_kampe funktion inde i hver tab)
    with tab_played:
        df_p = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False)
        tegn_kampe(df_p, True)

    with tab_fixtures:
        df_f = team_matches[team_matches['MATCH_STATUS'] == 'Fixture'].sort_values('MATCH_DATE_FULL', ascending=True)
        tegn_kampe(df_f, False)
        
    # --- 4. FORM BAR (Lige under top bar) ---
    form_html = "".join([f"<span class='form-dot {f['res']}' title='{f['hover']}'>{f['txt']}</span>" for f in stats["form"][-5:]])
    st.markdown(f"<div class='form-container' style='margin-bottom:10px;'>{form_html}</div>", unsafe_allow_html=True)
    
    st.divider()
    
    # --- 5. TABS TIL KAMPOVERSIGT ---
    tab_played, tab_fixtures = st.tabs(["Resultater", "Kommende kampe"])

    # Hjælpefunktion til at tegne kampene for at undgå dobbelt kode
    def tegn_kampe(matches, is_played):
        if matches.empty:
            st.info("Ingen kampe fundet.")
            return

        danske_dage = {"Monday": "MANDAG", "Tuesday": "TIRSDAG", "Wednesday": "ONSDAG", "Thursday": "TORSDAG", "Friday": "FREDAG", "Saturday": "LØRDAG", "Sunday": "SØNDAG"}
        danske_maaneder = {"January": "januar", "February": "februar", "March": "marts", "April": "april", "May": "maj", "June": "juni", "July": "juli", "August": "august", "September": "september", "October": "oktober", "November": "november", "December": "december"}

        current_date = None
        for _, row in matches.iterrows():
            d = pd.to_datetime(row['MATCH_DATE_FULL'])
            match_date = f"{danske_dage.get(d.strftime('%A'), d.strftime('%A'))} D. {d.day}. {danske_maaneder.get(d.strftime('%B'), d.strftime('%B'))}".upper()
            
            if match_date != current_date:
                st.markdown(f"<div class='date-header'>{match_date}</div>", unsafe_allow_html=True)
                current_date = match_date

            h_name = id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'])
            a_name = id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'])

            col1, col2, col3, col4, col5 = st.columns([2, 0.4, 1.2, 0.4, 2])
            with col1: st.markdown(f"<div style='text-align:right; font-weight:bold;'>{h_name}</div>", unsafe_allow_html=True)
            with col2: 
                h_logo = logos.get(h_name)
                if h_logo: st.image(h_logo, width=25)
            
            with col3:
                if is_played:
                    h_s = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
                    a_s = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
                    st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{h_s} - {a_s}</span></div>", unsafe_allow_html=True)
                else:
                    tid = str(row['MATCH_LOCALTIME'])[:5] if pd.notnull(row['MATCH_LOCALTIME']) else d.strftime('%H:%M')
                    st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{tid}</span></div>", unsafe_allow_html=True)

            with col4: 
                a_logo = logos.get(a_name)
                if a_logo: st.image(a_logo, width=25)
            with col5: st.markdown(f"<div style='text-align:left; font-weight:bold;'>{a_name}</div>", unsafe_allow_html=True)

    with tab_played:
        df_p = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False)
        tegn_kampe(df_p, True)

    with tab_fixtures:
        df_f = team_matches[team_matches['MATCH_STATUS'] == 'Fixture'].sort_values('MATCH_DATE_FULL', ascending=True)
        tegn_kampe(df_f, False)

    st.markdown("<div style='margin-bottom: 80px;'></div>", unsafe_allow_html=True)
