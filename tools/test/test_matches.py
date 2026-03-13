import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATAGRUNDLAG ---
    # Vi bruger nu 'team_stats' som vores primære kilde, da den indeholder alt
    df_matches = dp.get("opta", {}).get("team_stats", pd.DataFrame()).copy()

    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # Standardiser kolonnenavne
    df_matches.columns = [c.upper() for c in df_matches.columns]

    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "NordicBet Liga")

    maaned_map = {
        "Jan": "JANUAR", "Feb": "FEBRUAR", "Mar": "MARTS", "Apr": "APRIL", 
        "May": "MAJ", "Jun": "JUNI", "Jul": "JULI", "Aug": "AUGUST", 
        "Sep": "SEPTEMBER", "Oct": "OKTOBER", "Nov": "NOVEMBER", "Dec": "DECEMBER"
    }

    def safe_val(val, is_float=False):
        try:
            v = pd.to_numeric(val, errors='coerce')
            if pd.isna(v): return 0.0 if is_float else 0
            return float(v) if is_float else int(v)
        except: return 0

    # --- 2. CSS STYLING ---
    st.markdown("""
        <style>
        .stat-box { text-align: center; background: #f8f9fa; border-radius: 6px; padding: 8px; border-bottom: 3px solid #cc0000; }
        .stat-label { font-size: 11px; color: #666; text-transform: uppercase; font-weight: 600; }
        .stat-val { font-weight: 800; font-size: 16px; color: #111; }
        .date-header { background: #f0f0f0; padding: 6px 12px; border-radius: 4px; font-size: 13px; font-weight: bold; margin-top: 25px; border-left: 5px solid #cc0000; color: #333; }
        .score-pill { background: #222; color: white; border-radius: 4px; padding: 4px 12px; font-weight: bold; font-size: 18px; display: inline-block; min-width: 85px; text-align: center; }
        .formation-text { font-size: 11px; color: #888; font-weight: normal; margin-top: 2px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. HOLDVALG ---
    opta_to_name = {str(v['opta_uuid']).strip().upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())

    top_cols = st.columns([2.5, 0.5, 0.5, 0.5, 0.5, 0.6, 0.6, 0.6])
    with top_cols[0]:
        hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx, label_visibility="collapsed")
        valgt_uuid = str(liga_hold_options[valgt_navn]).strip().upper()

    # --- 4. FILTRERING ---
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # --- 5. KAMP-VISNING FUNKTION ---
    def tegn_kampe(df_list, spillet):
        for _, row in df_list.iterrows():
            # Dato-håndtering
            try:
                dt = pd.to_datetime(row.get('MATCH_DATE_FULL'))
                dato_str = f"{dt.day}. {maaned_map.get(dt.strftime('%b'), dt.strftime('%b').upper())} {dt.year}"
            except: dato_str = "Ukendt dato"

            st.markdown(f"<div class='date-header'>{dato_str} — RUNDE {safe_val(row.get('WEEK'))}</div>", unsafe_allow_html=True)

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 0.4, 1.2, 0.4, 2])
                
                h_name = opta_to_name.get(row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTHOME_NAME'])
                a_name = opta_to_name.get(row['CONTESTANTAWAY_OPTAUUID'], row['CONTESTANTAWAY_NAME'])

                # Hjemmehold info
                c1.markdown(f"""
                    <div style='text-align:right; font-weight:bold; padding-top:5px;'>
                        {h_name}<br><span class='formation-text'>{row.get('HOME_FORMATION', '')}</span>
                    </div>
                """, unsafe_allow_html=True)
                c2.image(TEAMS.get(h_name, {}).get('logo', ''), width=35)

                # Score / Tid
                if spillet:
                    c3.markdown(f"<div style='text-align:center;'><span class='score-pill'>{safe_val(row['TOTAL_HOME_SCORE'])} - {safe_val(row['TOTAL_AWAY_SCORE'])}</span></div>", unsafe_allow_html=True)
                else:
                    tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                    c3.markdown(f"<div style='text-align:center;'><span class='time-pill'>{tid}</span></div>", unsafe_allow_html=True)

                # Udehold info
                c4.image(TEAMS.get(a_name, {}).get('logo', ''), width=35)
                c5.markdown(f"""
                    <div style='text-align:left; font-weight:bold; padding-top:5px;'>
                        {a_name}<br><span class='formation-text'>{row.get('AWAY_FORMATION', '')}</span>
                    </div>
                """, unsafe_allow_html=True)

                if spillet:
                    st.markdown("<hr style='margin:10px 0; opacity:0.1;'>", unsafe_allow_html=True)
                    
                    # Mapping af de nye kolonner fra din Master Query
                    stats_to_draw = [
                        ("HOME_XG", "AWAY_XG", "Expected Goals (xG)", True),
                        ("HOME_POSS", "AWAY_POSS", "Boldbesiddelse", False, "%"),
                        ("HOME_SHOTS", "AWAY_SHOTS", "Afslutninger", False),
                        ("HOME_TOUCHES", "AWAY_TOUCHES", "Berøringer i feltet", False),
                        ("HOME_PASSES", "AWAY_PASSES", "Afleveringer", False)
                    ]

                    # Dynamiske farver fra Opta (eller fallback til Team Colors)
                    h_color = row.get('HOME_KIT', '#cc0000')
                    a_color = row.get('AWAY_KIT', '#222222')

                    for h_col, a_col, label, is_float, suffix in [
                        (s[0], s[1], s[2], s[3], s[4] if len(s)>4 else "") for s in stats_to_draw
                    ]:
                        h_val = safe_val(row.get(h_col), is_float)
                        a_val = safe_val(row.get(a_col), is_float)
                        
                        h_str = f"{h_val:.2f}{suffix}" if is_float else f"{int(h_val)}{suffix}"
                        a_str = f"{a_val:.2f}{suffix}" if is_float else f"{int(a_val)}{suffix}"

                        total = h_val + a_val
                        h_pct = (h_val / total * 100) if total > 0 else 50

                        st.markdown(f"""
                            <div style="margin-bottom: 12px;">
                                <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 2px;">
                                    <span style="font-weight: 800;">{h_str}</span>
                                    <span style="color: #888; text-transform: uppercase; font-size: 10px; font-weight: 600;">{label}</span>
                                    <span style="font-weight: 800;">{a_str}</span>
                                </div>
                                <div style="display: flex; height: 6px; background-color: #f0f0f0; border-radius: 3px; overflow: hidden;">
                                    <div style="width: {h_pct}%; background-color: {h_color};"></div>
                                    <div style="width: {100-h_pct}%; background-color: {a_color};"></div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

    # --- 6. TABS ---
    t1, t2 = st.tabs(["RESULTATER", "KOMMENDE"])
    with t1:
        tegn_kampe(played.sort_values('MATCH_DATE_FULL', ascending=False), True)
    with t2:
        future = team_matches[~team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
        tegn_kampe(future.sort_values('MATCH_DATE_FULL'), False)
