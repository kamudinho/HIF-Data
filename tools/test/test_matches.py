import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {}) # Hent logo-mappet her

    # --- FARVER & CSS ---
    hif_rod = "#df003b"
    st.markdown(f"""
        <style>
        .stat-box {{ text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }}
        .stat-label {{ font-size: 10px; color: gray; text-transform: uppercase; }}
        .stat-val {{ font-weight: bold; font-size: 14px; }}
        .form-dot {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 3px; }}
        .win {{ background-color: #28a745; }} .draw {{ background-color: #ffc107; }} .loss {{ background-color: #dc3545; }}
        /* Gør kamp-rækken pænere */
        .match-container {{ display: flex; align-items: center; gap: 10px; justify-content: center; }}
        </style>
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:15px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; font-size:1.1rem;">Betinia Ligaen: Stats & Kampe</h3>
        </div>
    """, unsafe_allow_html=True)

    # --- 1. FILTRE ---
    liga_hold = sorted([n for n, i in TEAMS.items() if i.get("league") in ["1. Division", "Betinia Ligaen", "NordicBet Liga"]])
    
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        valgt_hold = st.selectbox("Vælg hold", liga_hold)
    with col_f2:
        view_type = st.segmented_control("Vis", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. BEREGNING AF STATS ---
    all_played = df_matches[(df_matches['MATCH_STATUS'] == 'Played') & 
                            ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | 
                             (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))].sort_values('MATCH_DATE_FULL')

    stats = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0, "form": []}
    for _, m in all_played.iterrows():
        is_home = m['CONTESTANTHOME_NAME'] == valgt_hold
        m_plus = int(m['TOTAL_HOME_SCORE']) if is_home else int(m['TOTAL_AWAY_SCORE'])
        m_minus = int(m['TOTAL_AWAY_SCORE']) if is_home else int(m['TOTAL_HOME_SCORE'])
        stats["K"] += 1; stats["M+"] += m_plus; stats["M-"] += m_minus
        if m_plus > m_minus: stats["S"] += 1; stats["form"].append("win")
        elif m_plus == m_minus: stats["U"] += 1; stats["form"].append("draw")
        else: stats["N"] += 1; stats["form"].append("loss")

    # --- 3. VISNING AF STATS BAR ---
    st.markdown("#### Team Stats")
    c = st.columns([1.5, 0.6, 0.6, 0.6, 0.6, 0.8, 0.8, 0.8])
    with c[0]:
        st.markdown("<div class='stat-label'>Form (Sidste 5)</div>", unsafe_allow_html=True)
        form_html = "".join([f"<span class='form-dot {res}'></span>" for res in stats["form"][-5:]])
        st.markdown(f"<div>{form_html}</div>", unsafe_allow_html=True)
    
    labels = [("K", stats["K"]), ("S", stats["S"]), ("U", stats["U"]), ("N", stats["N"]), 
              ("M+", stats["M+"]), ("M-", stats["M-"]), ("+/-", stats["M+"]-stats["M-"])]
    for i, (label, val) in enumerate(labels):
        with c[i+1]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{label}</div><div class='stat-val'>{val}</div></div>", unsafe_allow_html=True)

    st.divider()

    # --- 4. KAMPOVERSIGT MED LOGOER ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    display_matches = df_matches[(df_matches['MATCH_STATUS'] == status_filter) & 
                                 ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | 
                                  (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    st.markdown(f"#### {view_type} Kampe")
    for _, row in display_matches.iterrows():
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        
        # Opret række med 5 kolonner for at centrere logoer og tekst perfekt
        col_date, col_h_logo, col_match, col_a_logo, col_res = st.columns([0.8, 0.4, 3, 0.4, 1])
        
        with col_date:
            st.write(f"📅 {row['MATCH_DATE_FULL'].strftime('%d/%m')}")
        
        with col_h_logo:
            st.image(logos.get(h_name, ""), width=25)
            
        with col_match:
            # Centreret tekst mellem logoerne
            st.markdown(f"<div style='text-align:center; font-size:0.95rem;'><b>{h_name}</b> vs. <b>{a_name}</b></div>", unsafe_allow_html=True)
            
        with col_a_logo:
            st.image(logos.get(a_name, ""), width=25)
        
        with col_res:
            if status_filter == 'Played':
                st.markdown(f"<div style='background:#333; color:white; border-radius:4px; text-align:center; font-weight:bold;'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='background:#f0f2f6; border-radius:4px; text-align:center; font-size:0.8rem;'>⏰ {row['MATCH_DATE_FULL'].strftime('%H:%M')}</div>", unsafe_allow_html=True)
