import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    """
    Viser kampside med resultater, kommende kampe og Opta-statistik.
    Modtager 'dp' som argument fra HIF-dash.py.
    """
    # 1. HENT DATA FRA PAKKEN
    # Vi bruger de nøgler, vi definerede i data_load.py
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_raw_stats = dp.get("team_stats_full", pd.DataFrame()) # Opta team stats
    logos = dp.get("logo_map", {})
    
    # Hent global konfiguration
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "NordicBet Liga")

   # --- DATA MERGE LOGIK (OPTA MATCHSTATS) ---
    if not df_raw_stats.empty and not df_matches.empty:
        try:
            # 1. Pivotér baseret på de præcise UUID kolonner fra databasen
            df_pivot = df_raw_stats.pivot_table(
                index=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                columns='STAT_TYPE', 
                values='STAT_TOTAL', 
                aggfunc='first'
            ).reset_index()

            # 2. Forbered Hjemme-stats (_HOME)
            # Vi fjerner join-nøglerne fra omdøbningen for at holde dem rene til merge
            df_home = df_pivot.copy()
            cols_to_rename = [c for c in df_home.columns if c not in ['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID']]
            df_home = df_home.rename(columns={c: f"{c}_HOME" for c in cols_to_rename})
            
            # 3. Forbered Ude-stats (_AWAY)
            df_away = df_pivot.copy()
            df_away = df_away.rename(columns={c: f"{c}_AWAY" for c in cols_to_rename})

            # 4. Merge Hjemme-stats på df_matches
            # Vi matcher kampens UUID + Hjemmeholdets UUID
            df_matches = pd.merge(
                df_matches, df_home, 
                left_on=['MATCH_OPTAUUID', 'CONTESTANTHOME_OPTAUUID'], 
                right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                how='left'
            ).drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')

            # 5. Merge Ude-stats på df_matches
            # Vi matcher kampens UUID + Udeholdets UUID
            df_matches = pd.merge(
                df_matches, df_away, 
                left_on=['MATCH_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID'], 
                right_on=['MATCH_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                how='left'
            ).drop(columns=['CONTESTANT_OPTAUUID'], errors='ignore')

        except Exception as e:
            st.error(f"⚠️ Fejl ved behandling af kampstatistik: {e}")

    # --- CSS STYLING ---
    hif_rod = "#cc0000"
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
    
    # Filtrer hold baseret på liga-navn fra config
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    
    if not liga_hold_options:
        st.warning(f"Ingen hold fundet i systemet for {valgt_liga_global}")
        return

    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    # Filtrer kampe for det valgte hold
    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()
    
    # Beregn Form og Stats (S-U-N)
    all_played = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL')
    stats = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0, "form": []}
    
    for _, m in all_played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        opp_name = id_to_name.get(m['CONTESTANTAWAY_OPTAUUID'] if is_h else m['CONTESTANTHOME_OPTAUUID'], "Modstander")
        h_s = int(m['TOTAL_HOME_SCORE']) if pd.notnull(m['TOTAL_HOME_SCORE']) else 0
        a_s = int(m['TOTAL_AWAY_SCORE']) if pd.notnull(m['TOTAL_AWAY_SCORE']) else 0
        
        stats["K"] += 1
        stats["M+"] += h_s if is_h else a_s
        stats["M-"] += a_s if is_h else h_s
        diff = h_s - a_s if is_h else a_s - h_s
        
        if diff > 0: stats["S"] += 1; stats["form"].append({"res":"win","txt":"S","hover":f"vs. {opp_name}"})
        elif diff == 0: stats["U"] += 1; stats["form"].append({"res":"draw","txt":"U","hover":f"vs. {opp_name}"})
        else: stats["N"] += 1; stats["form"].append({"res":"loss","txt":"N","hover":f"vs. {opp_name}"})

    # Vis Stats øverst
    stats_display = [("K", stats["K"]), ("S", stats["S"]), ("U", stats["U"]), ("N", stats["N"]), ("M+", stats["M+"]), ("M-", stats["M-"]), ("+/-", stats["M+"]-stats["M-"])]
    for i, (l, v) in enumerate(stats_display):
        with top_cols[i+1]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

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
                col1, col2, col3, col4, col5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                with col1: st.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{h_n}</div>", unsafe_allow_html=True)
                with col2: 
                    # Hent logo via WYID mapping (hvis muligt) eller brug standard
                    st.image(logos.get(row.get('CONTESTANTHOME_WYID'), HIF_LOGO_URL), width=28)
                with col3:
                    if is_played:
                        st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                    else:
                        tid = d.strftime('%H:%M')
                        st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{tid}</span></div>", unsafe_allow_html=True)
                with col4:
                    st.image(logos.get(row.get('CONTESTANTAWAY_WYID'), HIF_LOGO_URL), width=28)
                with col5: st.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{a_n}</div>", unsafe_allow_html=True)

                if is_played:
                    st.markdown("<hr style='margin: 10px 0; opacity: 0.1;'>", unsafe_allow_html=True)
                    s_col1, s_col2, s_col3, s_col4, s_col5 = st.columns(5)
                    
                    def stat_box(label, h_val, a_val, is_pct=False):
                        suffix = "%" if is_pct else ""
                        h_val = h_val if pd.notnull(h_val) else 0
                        a_val = a_val if pd.notnull(a_val) else 0
                        st.markdown(f"<div style='text-align:center;'><div style='font-size:9px; color:#888;'>{label}</div><div style='font-size:13px; font-weight:600;'>{h_val}{suffix} — {a_val}{suffix}</div></div>", unsafe_allow_html=True)

                    with s_col1: stat_box("Possession", row.get('possessionPercentage_HOME'), row.get('possessionPercentage_AWAY'), True)
                    with s_col2: stat_box("Passes", row.get('totalPass_HOME'), row.get('totalPass_AWAY'))
                    with s_col3: stat_box("Duels Won", row.get('wonTackle_HOME'), row.get('wonTackle_AWAY'))
                    with s_col4: stat_box("Scoring Att", row.get('totalScoringAtt_HOME'), row.get('totalScoringAtt_AWAY'))
                    with s_col5: stat_box("Tackles", row.get('totalTackle_HOME'), row.get('totalTackle_AWAY'))

    # --- 3. TABS ---
    tab_played, tab_fixtures = st.tabs(["Resultater", "Kommende kampe"])
    
    with tab_played:
        df_p = team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False)
        tegn_kampe(df_p, True)
    with tab_fixtures:
        df_f = team_matches[team_matches['MATCH_STATUS'] != 'Played'].sort_values('MATCH_DATE_FULL', ascending=True)
        tegn_kampe(df_f, False)

# Dummy logo fallback
HIF_LOGO_URL = "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"
