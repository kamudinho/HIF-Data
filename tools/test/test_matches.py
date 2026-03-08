import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. HENT OG FORBERED DATA ---
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_wy = dp.get("match_history", pd.DataFrame()).copy()
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # Standardiser kolonner
    df_matches.columns = [c.upper() for c in df_matches.columns]
    if not df_wy.empty:
        df_wy.columns = [c.upper() for c in df_wy.columns]
        df_wy['JOIN_KEY'] = pd.to_numeric(df_wy['GAMEWEEK'], errors='coerce').fillna(-1).astype(int)

    # --- 2. HOLDVALG (LØSNING PÅ hif_idx FEJL) ---
    opta_to_name = {v['opta_uuid']: k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())

    # Find index for Hvidovre, ellers 0
    try:
        hif_idx = h_list.index("Hvidovre")
    except ValueError:
        hif_idx = 0

    valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx)
    valgt_uuid = liga_hold_options[valgt_navn]
    valgt_hold_info = TEAMS.get(valgt_navn, {})
    valgt_wyid = valgt_hold_info.get('team_wyid')

    # Filtrer Wyscout til det valgte hold
    if not df_wy.empty and valgt_wyid:
        df_wy['TEAM_WYID'] = pd.to_numeric(df_wy['TEAM_WYID'], errors='coerce')
        df_wy = df_wy[df_wy['TEAM_WYID'] == int(valgt_wyid)].copy()

    # --- 3. BEREGN STATS TIL TOPBAR ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | 
                              (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.contains('Played', na=False)]
    
    st.markdown("### Oversigt")
    top_cols = st.columns(8)
    summary = {"K": len(played), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    
    for _, m in played.iterrows():
        is_h = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s = int(pd.to_numeric(m.get('TOTAL_HOME_SCORE'), errors='coerce') or 0)
        a_s = int(pd.to_numeric(m.get('TOTAL_AWAY_SCORE'), errors='coerce') or 0)
        summary["M+"] += h_s if is_h else a_s
        summary["M-"] += a_s if is_h else h_s
        diff = h_s - a_s if is_h else a_s - h_s
        if diff > 0: summary["S"] += 1
        elif diff == 0: summary["U"] += 1
        else: summary["N"] += 1

    stats_disp = [("K", summary["K"]), ("S", summary["S"]), ("U", summary["U"]), ("N", summary["N"]), ("M+", summary["M+"]), ("M-", summary["M-"]), ("+/-", summary["M+"]-summary["M-"])]
    for i, (l, v) in enumerate(stats_disp):
        top_cols[i+1].metric(l, v)

    # --- 4. TEGN KAMPE FUNKTION ---
    maaned_map = {"Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"}
    WY_STAT_MAP = {"POSSESSION": "Possession %", "TOUCHESINBOX": "Felt-touches", "SHOTS": "Skud", "XG": "xG", "PPDA": "PPDA", "RECOVERIES": "Erobringer"}

    def tegn_kampe(df_list, is_played):
        for _, row in df_list.iterrows():
            opta_week = int(pd.to_numeric(row.get('WEEK'), errors='coerce') or 0)
            wy_match_data = df_wy[df_wy['JOIN_KEY'] == opta_week] if not df_wy.empty else pd.DataFrame()
            
            # Dato-formatering
            dt = pd.to_datetime(row.get('MATCH_DATE_FULL'))
            dato_str = f"{dt.day}. {maaned_map.get(dt.strftime('%b'), 'UKENDT')} {dt.year}"
            
            st.info(f"{dato_str} — RUNDE {opta_week}")
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.5, 1, 0.5, 2])
                h_name = opta_to_name.get(row.get('CONTESTANTHOME_OPTAUUID'), "Hjemme")
                a_name = opta_to_name.get(row.get('CONTESTANTAWAY_OPTAUUID'), "Ude")
                
                c1.write(f"**{h_name}**")
                c2.image(TEAMS.get(h_name, {}).get('logo', '-'), width=30)
                if is_played:
                    c3.subheader(f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}")
                else:
                    c3.write(f"Kl. {str(row.get('MATCH_LOCALTIME'))[:5]}")
                c4.image(TEAMS.get(a_name, {}).get('logo', '-'), width=30)
                c5.write(f"**{a_name}**")

                if is_played and not wy_match_data.empty:
                    st.divider()
                    sc = st.columns(len(WY_STAT_MAP))
                    for i, (col, label) in enumerate(WY_STAT_MAP.items()):
                        val = wy_match_data.iloc[0].get(col, "-")
                        fmt = f"{float(val):.2f}" if col == "XG" and val != "-" else str(val)
                        sc[i].caption(label)
                        sc[i].write(f"**{fmt}**")

    # --- 5. TABS ---
    t1, t2 = st.tabs(["Resultater", "Program"])
    with t1:
        tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True)
    with t2:
        future = team_matches[~team_matches['MATCH_STATUS'].str.contains('Played', na=False)]
        tegn_kampe(future.sort_values('MATCH_DATE_FULL'), False)
