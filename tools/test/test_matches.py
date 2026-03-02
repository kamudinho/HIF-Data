import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    # Hent valgt liga fra pakken for at sikre match med TEAMS
    valgt_liga_global = dp.get("VALGT_LIGA", "1. Division")

    # --- CSS ---
    hif_rod = "#df003b"
    st.markdown(f"""
        <style>
        .stat-box {{ text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }}
        .stat-label {{ font-size: 10px; color: gray; text-transform: uppercase; }}
        .stat-val {{ font-weight: bold; font-size: 14px; }}
        .form-dot {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 3px; }}
        .win {{ background-color: #28a745; }} .draw {{ background-color: #ffc107; }} .loss {{ background-color: #dc3545; }}
        .date-header {{ background: #eee; padding: 5px 15px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #444; border-left: 4px solid {hif_rod}; }}
        .score-pill {{ background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; min-width: 70px; display: inline-block; text-align: center; }}
        .time-pill {{ background: #f0f2f6; color: #333; border-radius: 4px; padding: 2px 10px; font-size: 0.9rem; min-width: 70px; display: inline-block; text-align: center; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 1. FILTRE & OVERSÆTTER ---
    # Vi bygger en ordbog der mapper Opta UUID -> Dit Navn fra team_mapping.py
    # Dette er "broen" der sikrer at logoer findes.
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    
    # Filtrer hold baseret på den valgte liga (1. Division / Superliga)
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    
    if not liga_hold_options:
        st.warning(f"Ingen hold fundet for liga: {valgt_liga_global}")
        return

    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()))
        valgt_uuid = liga_hold_options[valgt_navn]
    with col_f2:
        view_type = st.segmented_control("Vis", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. DATA FILTRERING ---
    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | \
           (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()

    # --- 3. STATS BEREGNING ---
    all_played = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL')
    stats = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0, "form": []}
    
    for _, m in all_played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        try:
            h_s = int(m['TOTAL_HOME_SCORE']) if pd.notnull(m['TOTAL_HOME_SCORE']) else 0
            a_s = int(m['TOTAL_AWAY_SCORE']) if pd.notnull(m['TOTAL_AWAY_SCORE']) else 0
            stats["K"] += 1
            stats["M+"] += h_s if is_h else a_s
            stats["M-"] += a_s if is_h else h_s
            diff = h_s - a_s if is_h else a_s - h_s
            if diff > 0: stats["S"] += 1; stats["form"].append("win")
            elif diff == 0: stats["U"] += 1; stats["form"].append("draw")
            else: stats["N"] += 1; stats["form"].append("loss")
        except: continue

    # --- 4. VIS STATS BAR ---
    st.markdown(f"#### Stats for {valgt_navn}")
    c = st.columns([1.5, 0.6, 0.6, 0.6, 0.6, 0.8, 0.8, 0.8])
    with c[0]:
        st.markdown("<div class='stat-label'>Form</div>", unsafe_allow_html=True)
        form_html = "".join([f"<span class='form-dot {res}'></span>" for res in stats["form"][-5:]])
        st.markdown(f"<div>{form_html}</div>", unsafe_allow_html=True)
    
    stats_list = [("K", stats["K"]), ("S", stats["S"]), ("U", stats["U"]), ("N", stats["N"]), ("M+", stats["M+"]), ("M-", stats["M-"]), ("+/-", stats["M+"]-stats["M-"])]
    for i, (l, v) in enumerate(stats_list):
        with c[i+1]: st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    st.divider()

    # --- 5. KAMPOVERSIGT ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    display_matches = team_matches[team_matches['MATCH_STATUS'] == status_filter].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    if display_matches.empty:
        st.info(f"Ingen {view_type.lower()} kampe fundet.")
        return

    current_date = None
    for _, row in display_matches.iterrows():
        d = pd.to_datetime(row['MATCH_DATE_FULL'])
        match_date = d.strftime('%A d. %d. %B').upper()
        if match_date != current_date:
            st.markdown(f"<div class='date-header'>{match_date}</div>", unsafe_allow_html=True)
            current_date = match_date

        # Brug UUID til at finde DIT navn fra mapping, så logoet kan findes
        h_name = id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'])
        a_name = id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'])

        col1, col2, col3, col4, col5 = st.columns([2, 0.4, 1.2, 0.4, 2])
        with col1: st.markdown(f"<div style='text-align:right; font-weight:bold;'>{h_name}</div>", unsafe_allow_html=True)
        
        # SIKKER LOGO VISNING: Tjekker om URL findes før st.image kaldes
        with col2: 
            h_logo = logos.get(h_name)
            if h_logo: st.image(h_logo, width=25)
            
        with col3:
            if status_filter == 'Played':
                res = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}"
                st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{res}</span></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{d.strftime('%H:%M')}</span></div>", unsafe_allow_html=True)
        
        with col4: 
            a_logo = logos.get(a_name)
            if a_logo: st.image(a_logo, width=25)
            
        with col5: st.markdown(f"<div style='text-align:left; font-weight:bold;'>{a_name}</div>", unsafe_allow_html=True)
