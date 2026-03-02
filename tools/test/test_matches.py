import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})
    valgt_liga_global = dp.get("VALGT_LIGA", "1. division")

    # --- CSS (Nu med 'cursor: help' for at vise man kan hover) ---
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

    # --- 1. FILTRE ---
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
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

    # --- 3. STATS BEREGNING (Med hover-logik) ---
    all_played = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL')
    stats = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0, "form": []}
    
    for _, m in all_played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        # Find modstander
        opp_uuid = m['CONTESTANTAWAY_OPTAUUID'] if is_h else m['CONTESTANTHOME_OPTAUUID']
        opp_name = id_to_name.get(opp_uuid, m['CONTESTANTAWAY_NAME'] if is_h else m['CONTESTANTHOME_NAME'])
        
        try:
            h_s = int(m['TOTAL_HOME_SCORE']) if pd.notnull(m['TOTAL_HOME_SCORE']) else 0
            a_s = int(m['TOTAL_AWAY_SCORE']) if pd.notnull(m['TOTAL_AWAY_SCORE']) else 0
            stats["K"] += 1
            stats["M+"] += h_s if is_h else a_s
            stats["M-"] += a_s if is_h else h_s
            
            diff = h_s - a_s if is_h else a_s - h_s
            res_label = f"{h_s}-{a_s}"
            
            if diff > 0:
                stats["S"] += 1
                stats["form"].append({"res": "win", "txt": "S", "hover": f"Mod {opp_name} ({res_label})"})
            elif diff == 0:
                stats["U"] += 1
                stats["form"].append({"res": "draw", "txt": "U", "hover": f"Mod {opp_name} ({res_label})"})
            else:
                stats["N"] += 1
                stats["form"].append({"res": "loss", "txt": "N", "hover": f"Mod {opp_name} ({res_label})"})
        except: continue

    # --- 4. VIS STATS BAR ---
    st.markdown(f"### Statistik for {valgt_navn}")
    c = st.columns([1.5, 0.6, 0.6, 0.6, 0.6, 0.8, 0.8, 0.8])
    
    with c[0]:
        st.markdown("<div class='stat-label'>Form (Sidste 5)</div>", unsafe_allow_html=True)
        form_html = "".join([
            f"<span class='form-dot {f['res']}' title='{f['hover']}'>{f['txt']}</span>" 
            for f in stats["form"][-5:]
        ])
        st.markdown(f"<div class='form-container'>{form_html}</div>", unsafe_allow_html=True)
    
    stats_list = [("K", stats["K"]), ("S", stats["S"]), ("U", stats["U"]), ("N", stats["N"]), ("M+", stats["M+"]), ("M-", stats["M-"]), ("+/-", stats["M+"]-stats["M-"])]
    for i, (l, v) in enumerate(stats_list):
        with c[i+1]: st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    st.divider()

    # --- 5. KAMPOVERSIGT ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    display_matches = team_matches[team_matches['MATCH_STATUS'] == status_filter].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    if display_matches.empty:
        st.info(f"Ingen {view_type.lower()} kampe fundet.")
    else:
        danske_dage = {"Monday": "MANDAG", "Tuesday": "TIRSDAG", "Wednesday": "ONSDAG", "Thursday": "TORSDAG", "Friday": "FREDAG", "Saturday": "LØRDAG", "Sunday": "SØNDAG"}
        danske_maaneder = {"January": "januar", "February": "februar", "March": "marts", "April": "april", "May": "maj", "June": "juni", "July": "juli", "August": "august", "September": "september", "October": "oktober", "November": "november", "December": "december"}

        current_date = None
        for _, row in display_matches.iterrows():
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
                h_logo = logos.get(h_name); 
                if h_logo: st.image(h_logo, width=25)
            with col3:
                if status_filter == 'Played':
                    h_s = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
                    a_s = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
                    st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{h_s} - {a_s}</span></div>", unsafe_allow_html=True)
                else:
                    tid = str(row['MATCH_LOCALTIME'])[:5] if pd.notnull(row['MATCH_LOCALTIME']) else d.strftime('%H:%M')
                    st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{tid}</span></div>", unsafe_allow_html=True)
            with col4: 
                a_logo = logos.get(a_name); 
                if a_logo: st.image(a_logo, width=25)
            with col5: st.markdown(f"<div style='text-align:left; font-weight:bold;'>{a_name}</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 80px;'></div>", unsafe_allow_html=True)
