import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp")
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    st.markdown("### 🏟️ Match Center: 1. Division")

    # --- 1. FILTER: Kun Betinia Ligaen ---
    liga_hold = [navn for navn, info in TEAMS.items() if info.get("league") == "Betinia Ligaen"]
    liga_hold = sorted(liga_hold)

    col_f1, col_f2 = st.columns([2, 1])
    valgt_hold = col_f1.selectbox("Filtrer hold", ["Hele runden"] + liga_hold)
    view_type = col_f2.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. LOGIK ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    if valgt_hold != "Hele runden":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- 3. VISNING AF RÆKKER ---
    for _, row in display_df.head(15).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # Vi laver en container for at holde logo + expander tæt sammen
        with st.container(border=True):
            # Toppen af baren: Logoer og Navne (Altid synlig)
            c_header = st.columns([0.5, 2, 1, 2, 0.5])
            with c_header[0]:
                if logos.get(h_name): st.image(logos.get(h_name), width=25)
            with c_header[1]:
                st.markdown(f"**{h_name}**")
            with c_header[2]:
                st.markdown(f"<div style='text-align:center;'>{score}</div>", unsafe_allow_html=True)
            with c_header[3]:
                st.markdown(f"<div style='text-align:right;'>**{a_name}**</div>", unsafe_allow_html=True)
            with c_header[4]:
                if logos.get(a_name): st.image(logos.get(a_name), width=25)

            # Expander kun til data (Nu uden 'icon' for at undgå fejl)
            with st.expander("Se kampstatistik"):
                if status_filter == 'Played' and not df_stats.empty:
                    h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                    a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

                    def get_s(t_uuid, s_type):
                        return df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                                        (df_stats['CONTESTANT_OPTAUUID'] == t_uuid) & 
                                        (df_stats['STAT_TYPE'] == s_type)]['STAT_TOTAL'].sum()

                    # Data Visning
                    d1, d2, d3 = st.columns([1, 1, 1])
                    d1.metric("xG", f"{get_s(h_uuid, 'expectedGoals'):.2f}")
                    
                    with d2:
                        pos = get_s(h_uuid, 'possessionPercentage')
                        st.markdown("<p style='text-align:center;font-size:11px;'>Possession</p>", unsafe_allow_html=True)
                        st.progress(float(pos)/100 if pos else 0.5)
                        st.markdown(f"<p style='text-align:center;font-size:10px;'>{pos}% - {100-pos if pos else 50}%</p>", unsafe_allow_html=True)
                    
                    d3.write(f"<p style='text-align:right;'><b>xG</b><br>{get_s(a_uuid, 'expectedGoals'):.2f}</p>", unsafe_allow_html=True)
                else:
                    st.caption(f"Spilles på {row['VENUE_LONGNAME']} kl. {row['MATCH_DATE_FULL'].strftime('%H:%M')}")
