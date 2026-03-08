import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATA INDLÆSNING & FORBEREDELSE ---
    # Vi henter rådata fra data-provideren (dp)
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_wy = dp.get("match_history", pd.DataFrame()).copy()
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    if df_matches.empty:
        st.warning("Ingen kampdata fundet i Snowflake (OPTA).")
        return

    # Standardiser alle kolonnenavne til store bogstaver for at undgå KeyError
    df_matches.columns = [c.upper() for c in df_matches.columns]
    
    if not df_wy.empty:
        df_wy.columns = [c.upper() for c in df_wy.columns]
        # Vigtigt: Omdan GAMEWEEK til et rent heltal (JOIN_KEY) til matching
        df_wy['JOIN_KEY'] = pd.to_numeric(df_wy['GAMEWEEK'], errors='coerce').fillna(-1).astype(int)

    # --- 2. LOGIK FOR HOLDVALG ---
    # Vi mapper Opta UUID'er til navne fra din centrale TEAMS mapping
    opta_to_name = {v['opta_uuid']: k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    # Filtrer listen af hold baseret på den valgte liga i appen
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())

    # Hvidovre som standard, ellers det første i listen
    try:
        hif_idx = h_list.index("Hvidovre")
    except (ValueError, IndexError):
        hif_idx = 0

    valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx)
    valgt_uuid = liga_hold_options[valgt_navn]
    
    # Hent det tilsvarende Wyscout ID til senere filtrering af stats
    valgt_hold_info = TEAMS.get(valgt_navn, {})
    valgt_wyid = valgt_hold_info.get('team_wyid')

    # --- 3. FILTRERING & BEREGNING AF KSUN (BASERET PÅ OPTA) ---
    # Find alle kampe hvor det valgte hold er enten ude eller hjemme
    team_matches = df_matches[
        (df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | 
        (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)
    ].copy()

    # Opdel i spillede kampe og fremtidige kampe
    played = team_matches[team_matches['MATCH_STATUS'].str.contains('Played', na=False)].copy()
    future = team_matches[~team_matches['MATCH_STATUS'].str.contains('Played', na=False)].copy()
    
    # Beregn statistikken manuelt fra resultaterne
    summary = {"K": len(played), "S": 0, "U": 0, "N": 0, "M+": 0, "M-": 0}
    
    for _, m in played.iterrows():
        is_home = m['CONTESTANTHOME_OPTAUUID'] == valgt_uuid
        h_s = int(pd.to_numeric(m.get('TOTAL_HOME_SCORE'), errors='coerce') or 0)
        a_s = int(pd.to_numeric(m.get('TOTAL_AWAY_SCORE'), errors='coerce') or 0)
        
        # Målscore
        summary["M+"] += h_s if is_home else a_s
        summary["M-"] += a_s if is_home else h_s
        
        # S-U-N logik
        if h_s == a_s:
            summary["U"] += 1
        elif (is_home and h_s > a_s) or (not is_home and a_s > h_s):
            summary["S"] += 1
        else:
            summary["N"] += 1

    # Vis topbar med metrics
    st.markdown(f"### Oversigt: {valgt_navn}")
    m_cols = st.columns(7)
    metrics = [
        ("K", summary["K"]), ("S", summary["S"]), ("U", summary["U"]), 
        ("N", summary["N"]), ("M+", summary["M+"]), ("M-", summary["M-"]),
        ("+/-", summary["M+"]-summary["M-"])
    ]
    for i, (label, value) in enumerate(metrics):
        m_cols[i].metric(label, value)

    # --- 4. VISNINGS-FUNKTION TIL KAMPLISTE ---
    maaned_map = {
        "Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", 
        "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", 
        "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"
    }
    
    # De avancerede stats vi vil trække fra Wyscout hvis de findes
    WY_STAT_MAP = {
        "POSSESSION": "Possession %", 
        "XG": "xG", 
        "SHOTS": "Skud", 
        "TOUCHESINBOX": "Felt-touches", 
        "PPDA": "PPDA", 
        "RECOVERIES": "Erobringer"
    }

    def tegn_kampe(df_list, is_played_tab):
        if df_list.empty:
            st.info("Ingen kampe registreret i denne kategori.")
            return

        for _, row in df_list.iterrows():
            # Match-nøgle: Brug rundenummer (WEEK fra Opta)
            opta_week = int(pd.to_numeric(row.get('WEEK'), errors='coerce') or 0)
            
            # Find Wyscout data for præcis denne runde og dette hold
            wy_stats = pd.DataFrame()
            if not df_wy.empty and valgt_wyid:
                wy_stats = df_wy[
                    (df_wy['JOIN_KEY'] == opta_week) & 
                    (df_wy['TEAM_WYID'] == int(valgt_wyid))
                ]
            
            # Formatering af dato
            dt = pd.to_datetime(row.get('MATCH_DATE_FULL'))
            dato_str = f"{dt.day}. {maaned_map.get(dt.strftime('%b'), 'UKENDT')} {dt.year}"
            
            st.info(f"{dato_str} — RUNDE {opta_week}")
            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.5, 1.2, 0.5, 2])
                
                h_name = opta_to_name.get(row.get('CONTESTANTHOME_OPTAUUID'), row.get('CONTESTANTHOME_NAME'))
                a_name = opta_to_name.get(row.get('CONTESTANTAWAY_OPTAUUID'), row.get('CONTESTANTAWAY_NAME'))
                
                # Venstre side (Hjemmehold)
                c1.markdown(f"<div style='text-align:right; font-weight:bold;'>{h_name}</div>", unsafe_allow_html=True)
                c2.image(TEAMS.get(h_name, {}).get('logo', '-'), width=30)
                
                # Center (Resultat eller Tid)
                if is_played_tab:
                    h_score = int(row.get('TOTAL_HOME_SCORE', 0))
                    a_score = int(row.get('TOTAL_AWAY_SCORE', 0))
                    c3.markdown(f"<div style='text-align:center; font-size:20px; font-weight:800;'>{h_score} - {a_score}</div>", unsafe_allow_html=True)
                else:
                    tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                    c3.markdown(f"<div style='text-align:center; font-weight:bold;'>Kl. {tid}</div>", unsafe_allow_html=True)
                
                # Højre side (Udehold)
                c4.image(TEAMS.get(a_name, {}).get('logo', '-'), width=30)
                c5.markdown(f"<div style='text-align:left; font-weight:bold;'>{a_name}</div>", unsafe_allow_html=True)

                # --- WYSCOUT INTEGRATION (KUN HVIS KAMPEN ER SPILLET OG DATA FINDES) ---
                if is_played_tab and not wy_stats.empty:
                    st.divider()
                    s_cols = st.columns(len(WY_STAT_MAP))
                    for i, (col_key, label) in enumerate(WY_STAT_MAP.items()):
                        val = wy_stats.iloc[0].get(col_key, "-")
                        # Formatering af tal (f.eks. xG med 2 decimaler)
                        if col_key == "XG" and val != "-":
                            display_val = f"{float(val):.2f}"
                        elif col_key == "POSSESSION" and val != "-":
                            display_val = f"{int(val)}%"
                        else:
                            display_val = str(val)
                        
                        s_cols[i].caption(label)
                        s_cols[i].write(f"**{display_val}**")

    # --- 5. TABS VISNING ---
    t1, t2 = st.tabs(["⚽ Resultater", "📅 Program"])
    with t1:
        tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True)
    with t2:
        tegn_kampe(future.sort_values('MATCH_DATE_FULL', ascending=True), False)
