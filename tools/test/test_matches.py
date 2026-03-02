import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp")
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    st.markdown("### 🏟️ Match Center: 1. Division")

    # --- 1. FILTER ---
    liga_hold = [navn for navn, info in TEAMS.items() if info.get("league") == "Betinia Ligaen"]
    valgt_hold = st.selectbox("Filtrer hold", ["Hele runden"] + sorted(liga_hold))
    view_type = st.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. LOGIK ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    if valgt_hold != "Hele runden":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- 3. VISNING (Den store klikbare række) ---
    for _, row in display_df.head(15).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # Vi bygger en titel-streng uden Markdown (da expander-label ikke støtter kolonner/billeder direkte)
        # Men vi gør den ren og læselig
        label = f"{h_name}   {score}   {a_name}"
        
        # Vi bruger 'icon' til hjemmeholdet for at få billedet helt ud til venstre i baren
        with st.expander(label, icon=logos.get(h_name)):
            # Herinde viser vi dataen lynhurtigt og stramt
            if status_filter == 'Played' and not df_stats.empty:
                h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

                def get_s(t_uuid, s_type):
                    return df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                                    (df_stats['CONTESTANT_OPTAUUID'] == t_uuid) & 
                                    (df_stats['STAT_TYPE'] == s_type)]['STAT_TOTAL'].sum()

                # Selve data-sektionen (Ingen ikoner, rent layout)
                d1, d2, d3 = st.columns([1, 1, 1])
                
                with d1:
                    st.caption(h_name)
                    st.write(f"**xG:** {get_s(h_uuid, 'expectedGoals'):.2f}")
                    st.write(f"**Skud:** {int(get_s(h_uuid, 'totalShots'))}")

                with d2:
                    pos = get_s(h_uuid, 'possessionPercentage')
                    st.markdown("<p style='text-align:center; font-size:12px;'>Possession</p>", unsafe_allow_html=True)
                    st.progress(float(pos)/100 if pos else 0.5)
                    st.markdown(f"<p style='text-align:center; font-size:11px;'>{pos}% - {100-pos if pos else 50}%</p>", unsafe_allow_html=True)

                with d3:
                    st.markdown(f"<div style='text-align:right;'><span style='font-size:12px; color:gray;'>{a_name}</span><br><b>xG:</b> {get_s(a_uuid, 'expectedGoals'):.2f}<br><b>Skud:</b> {int(get_s(a_uuid, 'totalShots'))}</div>", unsafe_allow_html=True)
            else:
                st.caption(f"🏟️ {row['VENUE_LONGNAME']} | {row['MATCH_DATE_FULL'].strftime('%d. %b kl. %H:%M')}")
