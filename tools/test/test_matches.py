import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})

    # --- CSS & DESIGN ---
    hif_rod = "#df003b"
    st.markdown(f"""
        <style>
        .stat-box {{ text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }}
        .stat-label {{ font-size: 10px; color: gray; text-transform: uppercase; }}
        .stat-val {{ font-weight: bold; font-size: 14px; }}
        .form-dot {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 3px; }}
        .win {{ background-color: #28a745; }} .draw {{ background-color: #ffc107; }} .loss {{ background-color: #dc3545; }}
        .date-header {{ 
            background: #eee; padding: 5px 15px; border-radius: 4px; 
            font-size: 0.85rem; font-weight: bold; margin-top: 20px; margin-bottom: 10px;
            color: #444; border-left: 4px solid {hif_rod};
        }}
        .score-pill {{ background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; min-width: 70px; display: inline-block; text-align: center; }}
        .time-pill {{ background: #f0f2f6; color: #333; border-radius: 4px; padding: 2px 10px; font-size: 0.9rem; min-width: 70px; display: inline-block; text-align: center; }}
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"<div style='background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:15px;'><h3 style='color:white; margin:0; text-align:center; text-transform:uppercase; font-size:1.1rem;'>Betinia Ligaen: Stats & Kampe</h3></div>", unsafe_allow_html=True)

    # --- 1. FILTRE ---
    liga_hold = sorted([n for n, i in TEAMS.items() if i.get("league") in ["1. Division", "Betinia Ligaen", "NordicBet Liga"]])
    
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        valgt_hold = st.selectbox("Vælg hold", liga_hold)
    with col_f2:
        view_type = st.segmented_control("Vis", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. ROBUST DATA FILTRERING ---
    # Vi bruger 'contains' så "Hvidovre" matcher "Hvidovre IF"
    is_home = df_matches['CONTESTANTHOME_NAME'].str.contains(valgt_hold, case=False, na=False)
    is_away = df_matches['CONTESTANTAWAY_NAME'].str.contains(valgt_hold, case=False, na=False)
    team_matches = df_matches[is_home | is_away]

    # --- 3. BEREGNING AF STATS ---
    all_played = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL')
    
    stats = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0, "form": []}
    for _, m in all_played.iterrows():
        try:
            # Tjek om valgt hold var hjemme i denne specifikke kamp
            current_is_home = valgt_hold.lower() in m['CONTESTANTHOME_NAME'].lower()
            h_score = int(m['TOTAL_HOME_SCORE']) if pd.notnull(m['TOTAL_HOME_SCORE']) else 0
            a_score = int(m['TOTAL_AWAY_SCORE']) if pd.notnull(m['TOTAL_AWAY_SCORE']) else 0
            
            m_plus = h_score if current_is_home else a_score
            m_minus = a_score if current_is_home else h_score
            
            stats["K"] += 1
            stats["M+"] += m_plus
            stats["M-"] += m_minus
            
            if m_plus > m_minus: stats["S"] += 1; stats["form"].append("win")
            elif m_plus == m_minus: stats["U"] += 1; stats["form"].append("draw")
            else: stats["N"] += 1; stats["form"].append("loss")
        except: continue

    # --- 4. VISNING AF STATS BAR ---
    st.markdown("#### Team Stats")
    c = st.columns([1.5, 0.6, 0.6, 0.6, 0.6, 0.8, 0.8, 0.8])
    with c[0]:
        st.markdown("<div class='stat-label'>Form (Sidste 5)</div>", unsafe_allow_html=True)
        form_html = "".join([f"<span class='form-dot {res}'></span>" for res in stats["form"][-5:]])
        st.markdown(f"<div>{form_html}</div>", unsafe_allow_html=True)
    
    for i, (l, v) in enumerate([("K", stats["K"]), ("S", stats["S"]), ("U", stats["U"]), ("N", stats["N"]), ("M+", stats["M+"]), ("M-", stats["M-"]), ("+/-", stats["M+"]-stats["M-"])]):
        with c[i+1]: st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    st.divider()

    # --- 5. KAMPOVERSIGT ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    display_matches = team_matches[team_matches['MATCH_STATUS'] == status_filter].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    if display_matches.empty:
        st.info(f"Ingen kampe fundet for {valgt_hold}")
        return

    current_date = None
    for _, row in display_matches.iterrows():
        match_date = row['MATCH_DATE_FULL'].strftime('%A d. %d. %B')
        if match_date != current_date:
            st.markdown(f"<div class='date-header'>{match_date.upper()}</div>", unsafe_allow_html=True)
            current_date = match_date

        col1, col2, col3, col4, col5 = st.columns([2, 0.4, 1.2, 0.4, 2])
        with col1: st.markdown(f"<div style='text-align:right; font-weight:bold;'>{row['CONTESTANTHOME_NAME']}</div>", unsafe_allow_html=True)
        with col2: st.image(logos.get(row['CONTESTANTHOME_NAME'], ""), width=25)
        with col3:
            if status_filter == 'Played':
                res = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}"
                st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{res}</span></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{row['MATCH_DATE_FULL'].strftime('%H:%M')}</span></div>", unsafe_allow_html=True)
        with col4: st.image(logos.get(row['CONTESTANTAWAY_NAME'], ""), width=25)
        with col5: st.markdown(f"<div style='text-align:left; font-weight:bold;'>{row['CONTESTANTAWAY_NAME']}</div>", unsafe_allow_html=True)
