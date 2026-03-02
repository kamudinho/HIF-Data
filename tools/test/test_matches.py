import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    
    # --- HER SKAL LOGIKKEN IND ---
    # Vi antager df_stats er din rå liste med possessionPercentage, totalPass osv.
    if "opta_stats" in dp:
        df_stats = dp["opta_stats"]
        
        # 1. Pivotér stats så hver række er én kamp
        # Vi omdanner STAT_TYPE til kolonner
        df_stats_wide = df_stats.pivot(index='MATCH_ID', columns='STAT_TYPE', values='STAT_TOTAL').reset_index()
        
        # 2. Merge det på df_matches
        # Vi bruger 'left' for at beholde kampe, selvom de ikke har stats endnu (fixtures)
        df_matches = pd.merge(df_matches, df_stats_wide, left_on='MATCH_OPTAUUID', right_on='MATCH_ID', how='left')
    # ------------------------------

    logos = dp.get("logo_map", {})
    valgt_liga_global = dp.get("VALGT_LIGA", "1. division")
    
    # --- CSS ---
    hif_rod = "#df003b"
    st.markdown(f"""
        <style>
        .stat-box {{ text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }}
        .stat-label {{ font-size: 10px; color: gray; text-transform: uppercase; }}
        .stat-val {{ font-weight: bold; font-size: 14px; }}
        .form-container {{ display: flex; gap: 4px; }}
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

    # --- 1. DATA FORBEREDELSE & FILTRE ---
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    
    if not liga_hold_options:
        st.warning(f"Ingen hold fundet for liga: {valgt_liga_global}")
        return

    # Top Bar: Dropdown og Stats
    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    # Beregn data
    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()
    all_played = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL')
    
    stats = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0, "form": []}
    for _, m in all_played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        opp_name = id_to_name.get(m['CONTESTANTAWAY_OPTAUUID'] if is_h else m['CONTESTANTHOME_OPTAUUID'], "Modstander")
        try:
            h_s = int(m['TOTAL_HOME_SCORE']) if pd.notnull(m['TOTAL_HOME_SCORE']) else 0
            a_s = int(m['TOTAL_AWAY_SCORE']) if pd.notnull(m['TOTAL_AWAY_SCORE']) else 0
            stats["K"] += 1
            stats["M+"] += h_s if is_h else a_s
            stats["M-"] += a_s if is_h else h_s
            diff = h_s - a_s if is_h else a_s - h_s
            res_label = f"{h_s}-{a_s}"
            if diff > 0: stats["S"] += 1; stats["form"].append({"res":"win","txt":"S","hover":f"vs. {opp_name} ({res_label})"})
            elif diff == 0: stats["U"] += 1; stats["form"].append({"res":"draw","txt":"U","hover":f"vs. {opp_name} ({res_label})"})
            else: stats["N"] += 1; stats["form"].append({"res":"loss","txt":"N","hover":f"vs. {opp_name} ({res_label})"})
        except: continue

    # Tegn Stats
    stats_display = [("K", stats["K"]), ("S", stats["S"]), ("U", stats["U"]), ("N", stats["N"]), ("M+", stats["M+"]), ("M-", stats["M-"]), ("+/-", stats["M+"]-stats["M-"])]
    for i, (l, v) in enumerate(stats_display):
        with top_cols[i+1]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    st.write("") # Lille afstand

    # --- 2. HJÆLPEFUNKTION TIL KAMPE ---
    def tegn_kampe(matches, is_played):
        if matches.empty:
            st.info("Ingen kampe fundet.")
            return

        d_dage = {"Monday": "MANDAG", "Tuesday": "TIRSDAG", "Wednesday": "ONSDAG", "Thursday": "TORSDAG", "Friday": "FREDAG", "Saturday": "LØRDAG", "Sunday": "SØNDAG"}
        d_maaneder = {"January": "januar", "February": "februar", "March": "marts", "April": "april", "May": "maj", "June": "juni", "July": "juli", "August": "august", "September": "september", "October": "oktober", "November": "november", "December": "december"}

        current_date = None
        for _, row in matches.iterrows():
            d = pd.to_datetime(row['MATCH_DATE_FULL'])
            m_date = f"{d_dage.get(d.strftime('%A'), d.strftime('%A'))} D. {d.day}. {d_maaneder.get(d.strftime('%B'), d.strftime('%B'))}".upper()
            
            if m_date != current_date:
                st.markdown(f"<div class='date-header'>{m_date}</div>", unsafe_allow_html=True)
                current_date = m_date

            h_n = id_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'])
            a_n = id_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'])

            with st.container(border=True):
                # 1. LINJE: LOGOER OG SCORE
                col1, col2, col3, col4, col5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                with col1: st.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{h_n}</div>", unsafe_allow_html=True)
                with col2: 
                    h_l = logos.get(h_n)
                    if h_l: st.image(h_l, width=28)
                with col3:
                    if is_played:
                        st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                    else:
                        tid = str(row['MATCH_LOCALTIME'])[:5] if pd.notnull(row['MATCH_LOCALTIME']) else d.strftime('%H:%M')
                        st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{tid}</span></div>", unsafe_allow_html=True)
                with col4:
                    a_l = logos.get(a_n)
                    if a_l: st.image(a_l, width=28)
                with col5: st.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{a_n}</div>", unsafe_allow_html=True)

                # 2. LINJE: STATISTIK FRA DIN DATA (KUN HVIS SPILLET)
                if is_played:
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                    s_col1, s_col2, s_col3, s_col4, s_col5 = st.columns(5)
                    
                    def stat_box(label, h_val, a_val, is_pct=False):
                        suffix = "%" if is_pct else ""
                        st.markdown(f"""
                            <div style='text-align:center;'>
                                <div style='font-size:9px; color:#888; text-transform:uppercase;'>{label}</div>
                                <div style='font-size:13px; font-weight:600;'>{h_val}{suffix} — {a_val}{suffix}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    # Mapping af dine specifikke Opta-navne fra listen:
                    # OBS: Vi antager her at 'row' indeholder de aggregerede TOTAL-værdier.
                    with s_col1: 
                        stat_box("Possession", row.get('possessionPercentage_HOME', 0), row.get('possessionPercentage_AWAY', 0), True)
                    with s_col2: 
                        stat_box("Passes", row.get('totalPass_HOME', 0), row.get('totalPass_AWAY', 0))
                    with s_col3: 
                        # Duels er ofte summen af wonTackle eller en specifik Duel-stat
                        stat_box("Duels Won", row.get('wonTackle_HOME', 0), row.get('wonTackle_AWAY', 0))
                    with s_col4: 
                        # PPDA skal ofte beregnes eller hentes fra en specifik række
                        stat_box("Scoring Att", row.get('totalScoringAtt_HOME', 0), row.get('totalScoringAtt_AWAY', 0))
                    with s_col5: 
                        stat_box("Tackles", row.get('totalTackle_HOME', 0), row.get('totalTackle_AWAY', 0))
                        
    # --- 3. TABS OG FORM PÅ SAMME LINJE ---
    tab_col, form_col = st.columns([5, 1])
    with tab_col:
        tab_played, tab_fixtures = st.tabs(["Resultater", "Kommende kampe"])
    with form_col:
        f_html = "".join([f"<span class='form-dot {f['res']}' title='{f['hover']}'>{f['txt']}</span>" for f in stats["form"][-5:]])
        st.markdown(f"<div style='display: flex; justify-content: flex-end; margin-top: 12px;'><div class='form-container'>{f_html}</div></div>", unsafe_allow_html=True)

    # --- 4. INDHOLD I TABS ---
    with tab_played:
        df_p = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False)
        tegn_kampe(df_p, True)
    with tab_fixtures:
        df_f = team_matches[team_matches['MATCH_STATUS'] == 'Fixture'].sort_values('MATCH_DATE_FULL', ascending=True)
        tegn_kampe(df_f, False)

    st.markdown("<div style='margin-bottom: 80px;'></div>", unsafe_allow_html=True)
