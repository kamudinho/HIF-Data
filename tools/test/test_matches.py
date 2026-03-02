import streamlit as st
import pandas as pd

def vis_side():
    dp = st.session_state.get("dp")
    df = dp.get("opta_matches", pd.DataFrame())
    # Vi bruger nu også de rå stats, vi hentede tidligere
    df_stats = dp.get("opta_raw_stats", pd.DataFrame()) 
    logos = dp.get("logo_map", {})

    st.markdown("### 🏟️ Match Center: 1. Division")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        view_type = st.radio("Visning", ["Seneste Resultater", "Kommende Kampe"], horizontal=True)
    
    if view_type == "Seneste Resultater":
        display_df = df[df['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False)
    else:
        display_df = df[df['MATCH_STATUS'] == 'Fixture'].sort_values('MATCH_DATE_FULL', ascending=True)

    for _, row in display_df.head(15).iterrows():
        match_id = row['MATCH_OPTAUUID']
        
        with st.container(border=True):
            st.caption(f"📅 {row['MATCH_DATE_FULL'].strftime('%d. %b %Y')} | 🏟️ {row['VENUE_LONGNAME']}")
            
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 2])
            
            # Hjemmehold
            home_team = row['CONTESTANTHOME_NAME']
            c1.image(logos.get(home_team, ""), width=40)
            c1.markdown(f"**{home_team}**")
            
            # Score
            if row['MATCH_STATUS'] == 'Played':
                score_html = f"<div style='text-align:center; background-color:#1e1e1e; color:white; padding:10px; border-radius:5px; font-size:20px; font-weight:bold;'>{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}</div>"
                c3.markdown(score_html, unsafe_allow_html=True)
            else:
                c3.markdown("<div style='text-align:center; padding-top:10px;'>VS</div>", unsafe_allow_html=True)
            
            # Udehold
            away_team = row['CONTESTANTAWAY_NAME']
            c5.image(logos.get(away_team, ""), width=40)
            c5.markdown(f"<div style='text-align:right;'>**{away_team}**</div>", unsafe_allow_html=True)

            # --- NY SEKTION: HOLD DATA (OPTA) ---
            if row['MATCH_STATUS'] == 'Played' and not df_stats.empty:
                # Find stats for denne specifikke kamp
                m_stats = df_stats[df_stats['MATCH_OPTAUUID'] == match_id]
                
                if not m_stats.empty:
                    with st.expander("📊 Se kamp-statistik (Opta)"):
                        # Vi laver en hurtig sammenligning af de vigtigste tal
                        # Antager vi har 'STAT_TYPE' og 'STAT_VALUE' i df_stats
                        col_stat1, col_stat2, col_stat3 = st.columns([1, 1, 1])
                        
                        # Eksempel: xG (hvis den findes i jeres Opta-feed)
                        xg_home = m_stats[(m_stats['CONTESTANT_NAME'] == home_team) & (m_stats['STAT_TYPE'] == 'expected_goals')]['STAT_VALUE'].sum()
                        xg_away = m_stats[(m_stats['CONTESTANT_NAME'] == away_team) & (m_stats['STAT_TYPE'] == 'expected_goals')]['STAT_VALUE'].sum()
                        
                        col_stat1.metric(f"xG {home_team}", round(xg_home, 2))
                        col_stat2.markdown("<div style='text-align:center; padding-top:25px;'>EXPECTED GOALS</div>", unsafe_allow_html=True)
                        col_stat3.metric(f"xG {away_team}", round(xg_away, 2))
            
            if row['ATTENDANCE'] > 0:
                st.caption(f"👥 Tilskuere: {int(row['ATTENDANCE']):,}")
