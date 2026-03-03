import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(dp):
    """
    Viser kampside med resultater, kommende kampe og Opta-statistik.
    Fuldt opdateret til at håndtere NaT-fejl og korrekte tidspunkter.
    """
    # 1. HENT DATA FRA PAKKEN
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_raw_stats = dp.get("team_stats_full", pd.DataFrame()) 
    
    if df_matches.empty:
        st.warning("Ingen kampdata fundet i systemet.")
        return

    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    # --- DANSKE DATOER HJÆLPERE ---
    danske_dage = {
        "Monday": "Mandag", "Tuesday": "Tirsdag", "Wednesday": "Onsdag",
        "Thursday": "Torsdag", "Friday": "Fredag", "Saturday": "Lørdag", "Sunday": "Søndag"
    }
    danske_maaneder = {
        "January": "januar", "February": "februar", "March": "marts",
        "April": "april", "May": "maj", "June": "juni",
        "July": "juli", "August": "august", "September": "september",
        "October": "oktober", "November": "november", "December": "december"
    }

    # --- LOGO FUNKTION ---
    def hent_hold_logo(opta_uuid):
        logo_map = dp.get("logo_map", {})
        target_uuid = str(opta_uuid).lower().strip()
        for name, info in TEAMS.items():
            if str(info.get("opta_uuid", "")).lower().strip() == target_uuid:
                wy_id = info.get("team_wyid") or info.get("TEAM_WYID")
                if wy_id and int(wy_id) in logo_map: return logo_map[int(wy_id)]
                if info.get("logo") and info.get("logo") != "-": return info.get("logo")
        return "https://cdn5.wyscout.com/photos/team/public/2659_120x120.png"

    # --- CSS STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f0f2f6; border-radius: 4px; padding: 5px; min-width: 35px; }
        .stat-label { font-size: 10px; color: gray; text-transform: uppercase; }
        .stat-val { font-weight: bold; font-size: 14px; }
        .date-header { background: #eee; padding: 5px 15px; border-radius: 4px; font-size: 0.85rem; font-weight: bold; margin-top: 20px; margin-bottom: 10px; color: #444; border-left: 4px solid #cc0000; }
        .score-pill { background: #333; color: white; border-radius: 4px; padding: 2px 10px; font-weight: bold; min-width: 70px; display: inline-block; text-align: center; }
        .time-pill { background: #f0f2f6; color: #333; border-radius: 4px; padding: 2px 10px; font-size: 0.9rem; min-width: 70px; display: inline-block; text-align: center; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    # --- FILTRE & MASKERING ---
    id_to_name = {i.get("opta_uuid"): n for n, i in TEAMS.items() if i.get("opta_uuid")}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    
    if not liga_hold_options:
        st.warning(f"Ingen hold fundet for {valgt_liga_global}.")
        return

    top_cols = st.columns([2.2, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        valgt_navn = st.selectbox("Vælg hold", sorted(liga_hold_options.keys()), label_visibility="collapsed")
        valgt_uuid = liga_hold_options[valgt_navn]

    mask = (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    team_matches = df_matches[mask].copy()

    # --- STATISTIK BEREGNING (OVERBLIK) ---
    stats = {"K": 0, "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    for _, m in team_matches[team_matches['MATCH_STATUS'] == 'Played'].iterrows():
        try:
            is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
            h_s = int(m.get('TOTAL_HOME_SCORE', 0)) if pd.notnull(m.get('TOTAL_HOME_SCORE')) else 0
            a_s = int(m.get('TOTAL_AWAY_SCORE', 0)) if pd.notnull(m.get('TOTAL_AWAY_SCORE')) else 0
            stats["K"] += 1
            stats["M+"] += h_s if is_h else a_s
            stats["M-"] += a_s if is_h else h_s
            diff = h_s - a_s if is_h else a_s - h_s
            if diff > 0: stats["S"] += 1
            elif diff == 0: stats["U"] += 1
            else: stats["N"] += 1
        except: continue

    stats_disp = [("K", stats["K"]), ("S", stats["S"]), ("U", stats["U"]), ("N", stats["N"]), ("M+", stats["M+"]), ("M-", stats["M-"]), ("+/-", stats["M+"]-stats["M-"])]
    for i, (l, v) in enumerate(stats_disp):
        with top_cols[i+1]:
            st.markdown(f"<div class='stat-box'><div class='stat-label'>{l}</div><div class='stat-val'>{v}</div></div>", unsafe_allow_html=True)

    # --- KAMPLISTE FUNKTION ---
    def tegn_kampe(df, played):
        if df.empty:
            st.info("Ingen kampe fundet i denne kategori.")
            return
            
        for _, row in df.iterrows():
            try:
                # 1. Håndter Dato (Spring over hvis NaT)
                dt_raw = row.get('MATCH_LOCALDATE')
                if pd.isna(dt_raw) or str(dt_raw) == "NaT": continue
                
                dt = pd.to_datetime(dt_raw)
                dag = danske_dage.get(dt.strftime('%A'), dt.strftime('%A'))
                maaned = danske_maaneder.get(dt.strftime('%B'), dt.strftime('%B'))
                st.markdown(f"<div class='date-header'>{dag.upper()} D. {dt.day}. {maaned.upper()}</div>", unsafe_allow_html=True)

                # 2. Håndter Tid
                t_raw = str(row.get('MATCH_LOCALTIME', ''))
                t_disp = t_raw[:5] if ":" in t_raw else "TBA"

                h_uuid, a_uuid = row.get('CONTESTANTHOME_OPTAUUID'), row.get('CONTESTANTAWAY_OPTAUUID')
                h_n = id_to_name.get(h_uuid, row.get('CONTESTANTHOME_NAME'))
                a_n = id_to_name.get(a_uuid, row.get('CONTESTANTAWAY_NAME'))

                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                    c1.markdown(f"<div style='text-align:right; font-weight:bold; margin-top:5px;'>{h_n}</div>", unsafe_allow_html=True)
                    c2.image(hent_hold_logo(h_uuid), width=28)
                    with c3:
                        if played:
                            st.markdown(f"<div style='text-align:center;'><span class='score-pill'>{int(row.get('TOTAL_HOME_SCORE',0))} - {int(row.get('TOTAL_AWAY_SCORE',0))}</span></div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='text-align:center;'><span class='time-pill'>{t_disp}</span></div>", unsafe_allow_html=True)
                    c4.image(hent_hold_logo(a_uuid), width=28)
                    c5.markdown(f"<div style='text-align:left; font-weight:bold; margin-top:5px;'>{a_n}</div>", unsafe_allow_html=True)
            except: continue

    # --- TABS VISNING ---
    tab_res, tab_fix = st.tabs(["Resultater", "Kommende kampe"])
    with tab_res:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False), True)
    with tab_fix:
        tegn_kampe(team_matches[team_matches['MATCH_STATUS'] != 'Played'].sort_values('MATCH_DATE_FULL'), False)
