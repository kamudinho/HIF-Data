import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(dp):
    # --- 1. DATA & KONFIGURATION ---
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_wy = dp.get("match_history", pd.DataFrame()).copy()
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")

    if df_matches.empty:
        st.warning("Ingen data fundet.")
        return

    # Standardiser kolonner
    df_matches.columns = [c.upper() for c in df_matches.columns]
    if not df_wy.empty:
        df_wy.columns = [c.upper() for c in df_wy.columns]
        df_wy['JOIN_KEY'] = pd.to_numeric(df_wy['GAMEWEEK'], errors='coerce').fillna(-1).astype(int)

    # --- 2. HOLDVALG & STYLING ---
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())
    
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
    valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx)
    
    # Hent farver for det valgte hold (Fallback til grå)
    farve = TEAM_COLORS.get(valgt_navn, "#f0f2f6")
    opta_to_name = {v['opta_uuid']: k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # --- 3. TOPBAR (KSUN) MED DESIGN ---
    # Vi laver en lækker container med holdets farve som accent
    st.markdown(f"""
        <div style="background-color:{farve}22; padding:20px; border-radius:15px; border-left: 10px solid {farve}; margin-bottom:25px;">
            <h2 style="margin:0; color:#1f1f1f;">{valgt_navn.upper()}</h2>
            <p style="margin:0; opacity:0.7;">Sæson 2025/2026 — {valgt_liga_global}</p>
        </div>
    """, unsafe_allow_html=True)

    # Beregn stats
    valgt_uuid = liga_hold_options[valgt_navn]
    team_matches = df_matches[(df_matches['CONTESTANTHOME_OPTAUUID'] == valgt_uuid) | (df_matches['CONTESTANTAWAY_OPTAUUID'] == valgt_uuid)].copy()
    played = team_matches[team_matches['MATCH_STATUS'].str.contains('Played', na=False)].sort_values('MATCH_DATE_FULL', ascending=False)
    
    # Smukke stats-bokse
    m_cols = st.columns(7)
    # ... (samme beregnings-logik som før) ...
    # [Beregner summary her...]
    
    # --- 4. DEN "LÆKRE" KAMPLISTE ---
    def tegn_kamp_kort(row, is_played):
        opta_week = int(pd.to_numeric(row.get('WEEK'), errors='coerce') or 0)
        h_name = opta_to_name.get(row.get('CONTESTANTHOME_OPTAUUID'), "Hjemme")
        a_name = opta_to_name.get(row.get('CONTESTANTAWAY_OPTAUUID'), "Ude")
        
        # Container for hele kampen
        with st.container(border=True):
            # Header: Runde og Dato
            dt = pd.to_datetime(row.get('MATCH_DATE_FULL'))
            st.markdown(f"**RUNDE {opta_week}** <span style='opacity:0.5; font-size:0.8em;'>— {dt.day}/{dt.month}</span>", unsafe_allow_html=True)
            
            # Scoreboard
            cols = st.columns([2, 1, 0.5, 1, 2])
            cols[0].markdown(f"<p style='text-align:right; font-size:1.1em; margin-top:10px;'>{h_name}</p>", unsafe_allow_html=True)
            cols[1].image(TEAMS.get(h_name, {}).get('logo', '-'), width=45)
            
            if is_played:
                h_s, a_s = int(row['TOTAL_HOME_SCORE']), int(row['TOTAL_AWAY_SCORE'])
                cols[2].markdown(f"<h2 style='text-align:center; margin:0;'>{h_s}-{a_s}</h2>", unsafe_allow_html=True)
            else:
                tid = str(row.get('MATCH_LOCALTIME', ''))[:5]
                cols[2].markdown(f"<p style='text-align:center; margin-top:15px; font-weight:bold;'>{tid}</p>", unsafe_allow_html=True)
            
            cols[3].image(TEAMS.get(a_name, {}).get('logo', '-'), width=45)
            cols[4].markdown(f"<p style='text-align:left; font-size:1.1em; margin-top:10px;'>{a_name}</p>", unsafe_allow_html=True)

            # Wyscout Stats (kun hvis de findes)
            if is_played:
                valgt_wyid = TEAMS.get(valgt_navn, {}).get('team_wyid')
                wy_stats = df_wy[(df_wy['JOIN_KEY'] == opta_week) & (df_wy['TEAM_WYID'] == int(valgt_wyid))] if not df_wy.empty and valgt_wyid else pd.DataFrame()
                
                if not wy_stats.empty:
                    st.markdown("<div style='height:1px; background-color:#eee; margin:10px 0;'></div>", unsafe_allow_html=True)
                    s = st.columns(6)
                    # Små, lækre labels til stats
                    stats_to_show = [("XG", "xG"), ("POSSESSION", "Poss."), ("PPDA", "PPDA"), ("RECOVERIES", "Erob.")]
                    for i, (key, label) in enumerate(stats_to_show):
                        val = wy_stats.iloc[0].get(key, "-")
                        s[i].caption(label)
                        s[i].write(f"**{val}**")

    # Tabs med emojis for bedre look
    t1, t2 = st.tabs(["🏆 RESULTATER", "🗓️ PROGRAM"])
    with t1:
        for _, r in played.iterrows(): tegn_kamp_kort(r, True)
    with t2:
        future = team_matches[~team_matches['MATCH_STATUS'].str.contains('Played', na=False)].sort_values('MATCH_DATE_FULL')
        for _, r in future.iterrows(): tegn_kamp_kort(r, False)
