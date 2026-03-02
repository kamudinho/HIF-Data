import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp")
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    st.markdown("### 🏟️ Opta Match Center")

    # --- 1. FILTRE ---
    alle_hold = sorted(list(TEAMS.keys())) # Vi bruger listen fra din mapping
    col1, col2 = st.columns([2, 1])
    valgt_hold = col1.selectbox("Filtrer hold", ["Alle hold"] + alle_hold)
    view_type = col2.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. LOGIK ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = df_matches['MATCH_STATUS'] == status_filter
    
    if valgt_hold != "Alle hold":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- 3. KOMPAKT LISTE ---
    for _, row in display_df.head(20).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        
        # Hent UUIDs fra din mapping-fil
        h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
        a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')
        
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # Expander bar med logo fra map
        with st.expander(f"{h_name}  {score}  {a_name}", icon=logos.get(h_name)):
            if status_filter == 'Played' and not df_stats.empty:
                
                # Hjælpefunktion der bruger UUID i stedet for Navn (Meget mere sikkert!)
                def get_stat(t_uuid, s_type):
                    val = df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                                  (df_stats['CONTESTANT_OPTAUUID'] == t_uuid) & 
                                  (df_stats['STAT_TYPE'] == s_type)]['STAT_TOTAL'].sum()
                    return val

                # Rigtige data-opslag
                h_xg, a_xg = get_stat(h_uuid, 'expectedGoals'), get_stat(a_uuid, 'expectedGoals')
                h_pos, a_pos = get_stat(h_uuid, 'possessionPercentage'), get_stat(a_uuid, 'possessionPercentage')

                # Visning (Rå data, ingen ikoner)
                c1, c2, c3 = st.columns([1, 1, 1])
                c1.metric("xG", f"{h_xg:.2f}")
                
                with c2:
                    st.markdown(f"<p style='text-align:center;font-size:12px;'>Possession</p>", unsafe_allow_html=True)
                    st.progress(float(h_pos)/100 if h_pos else 0.5)
                    st.markdown(f"<p style='text-align:center;font-size:11px;'>{h_pos}% - {a_pos}%</p>", unsafe_allow_html=True)
                
                c3.write(f"<p style='text-align:right;'><b>xG</b><br>{a_xg:.2f}</p>", unsafe_allow_html=True)
            else:
                st.caption(f"Spilles på {row['VENUE_LONGNAME']}")
