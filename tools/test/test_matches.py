import streamlit as st
import pandas as pd

def vis_side():
    dp = st.session_state.get("dp")
    df = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})

    st.markdown("### 🏟️ Match Center: 1. Division")
    
    # Filtre i toppen
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        view_type = st.radio("Visning", ["Seneste Resultater", "Kommende Kampe"], horizontal=True)
    
    # Filtrering baseret på status
    if view_type == "Seneste Resultater":
        display_df = df[df['MATCH_STATUS'] == 'Played'].sort_values('MATCH_DATE_FULL', ascending=False)
    else:
        display_df = df[df['MATCH_STATUS'] == 'Fixture'].sort_values('MATCH_DATE_FULL', ascending=True)

    for _, row in display_df.head(15).iterrows():
        with st.container(border=True):
            # Header: Dato og Stadion
            st.caption(f"📅 {row['MATCH_DATE_FULL'].strftime('%d. %b %Y')} | 🏟️ {row['VENUE_LONGNAME']}")
            
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 2])
            
            # Hjemmehold
            home_team = row['CONTESTANTHOME_NAME']
            home_logo = logos.get(home_team, "https://cdn.pixabay.com/photo/2016/03/31/19/21/ball-1294935_1280.png")
            c1.image(home_logo, width=40)
            c1.markdown(f"**{home_team}**")
            
            # Score eller VS
            if row['MATCH_STATUS'] == 'Played':
                score_html = f"""
                    <div style='text-align:center; background-color:#1e1e1e; color:white; 
                         padding:10px; border-radius:5px; font-size:20px; font-weight:bold;'>
                        {int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}
                    </div>
                """
                c3.markdown(score_html, unsafe_allow_html=True)
            else:
                c3.markdown("<div style='text-align:center; padding-top:10px;'>VS</div>", unsafe_allow_html=True)
            
            # Udehold
            away_team = row['CONTESTANTAWAY_NAME']
            away_logo = logos.get(away_team, "https://cdn.pixabay.com/photo/2016/03/31/19/21/ball-1294935_1280.png")
            c5.image(away_logo, width=40)
            c5.markdown(f"<div style='text-align:right;'>**{away_team}**</div>", unsafe_allow_html=True)
            
            # Ekstra data (Attendance)
            if row['MATCH_STATUS'] == 'Played' and row['ATTENDANCE'] > 0:
                st.caption(f"👥 Tilskuere: {int(row['ATTENDANCE']):,}")
