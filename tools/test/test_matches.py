import streamlit as st
import pandas as pd

def vis_side():
    dp = st.session_state.get("dp")
    df = dp.get("opta_matches", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    # Vi henter de rå stats (husk at tjekke om de findes i din get_data_package)
    df_stats = dp.get("opta_team_stats", pd.DataFrame())

    st.markdown("### 🏟️ Match Center: 1. Division")
    
    view_type = st.radio("Visning", ["Seneste Resultater", "Kommende Kampe"], horizontal=True)
    
    display_df = df[df['MATCH_STATUS'] == ('Played' if view_type == "Seneste Resultater" else 'Fixture')]
    display_df = display_df.sort_values('MATCH_DATE_FULL', ascending=(view_type != "Seneste Resultater"))

    for _, row in display_df.head(10).iterrows():
        with st.container(border=True):
            # Layout for selve kampen (Logoer og Score)
            c1, c2, c3 = st.columns([2, 1, 2])
            
            # Hjemmehold
            h_name = row['CONTESTANTHOME_NAME']
            c1.image(logos.get(h_name, "https://cdn.pixabay.com/photo/2016/03/31/19/21/ball-1294935_1280.png"), width=40)
            c1.subheader(h_name)

            # Score i midten
            if row['MATCH_STATUS'] == 'Played':
                score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}"
                c2.markdown(f"<h2 style='text-align:center;'>{score}</h2>", unsafe_allow_html=True)
            else:
                c2.markdown("<h2 style='text-align:center;'>VS</h2>", unsafe_allow_html=True)

            # Udehold
            a_name = row['CONTESTANTAWAY_NAME']
            c3.image(logos.get(a_name, ""), width=40)
            c3.subheader(a_name)

            # --- HER ÅBNER VI DATAEN ---
            if row['MATCH_STATUS'] == 'Played':
                with st.expander("📊 DYK NED I DATA (OPTA)"):
                    # Her simulerer vi Opta-stats (indtil vi har mappet din opta_team_stats tabel helt)
                    # Vi laver en bar-chart sammenligning
                    st.write("**Boldbesiddelse %**")
                    # Eksempel: Vi fordeler 100% (Dette skal erstattes med rigtige tal fra df_stats)
                    col_stat_h, col_stat_a = st.columns([50, 50]) 
                    col_stat_h.markdown("<div style='background:#cc0000; height:10px; border-radius:5px 0 0 5px;'></div>", unsafe_allow_html=True)
                    col_stat_a.markdown("<div style='background:#333333; height:10px; border-radius:0 5px 5px 0;'></div>", unsafe_allow_html=True)
                    
                    st.divider()
                    
                    # Visning af xG (Expected Goals)
                    st.write("**Expected Goals (xG)**")
                    st.columns(2)[0].metric(h_name, "1.42")
                    st.columns(2)[1].metric(a_name, "0.85")

            st.caption(f"🏟️ {row['VENUE_LONGNAME']} | 👥 {int(row['ATTENDANCE']):,} tilskuere")
