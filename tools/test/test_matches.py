import streamlit as st
import pandas as pd

def vis_side():
    dp = st.session_state.get("dp")
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame()) # Her bor den rigtige data
    logos = dp.get("logo_map", {})
    
    st.markdown("### 🏟️ Opta Match Center")

    # --- 1. FILTRE ---
    alle_hold = sorted(pd.concat([df_matches['CONTESTANTHOME_NAME'], df_matches['CONTESTANTAWAY_NAME']]).unique())
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
        m_id = row['MATCH_OPTAUUID']
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        
        # Hent logoer - fallback til bold hvis de ikke findes
        h_logo = logos.get(h_name, "⚽")
        
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # Vi placerer hjemmeholdets logo i baren via 'icon'
        with st.expander(f"{h_name}  {score}  {a_name}", icon=h_logo):
            
            if status_filter == 'Played':
                # HENT RIGTIG DATA FRA SNOWFLAKE (df_stats)
                match_stats = df_stats[df_stats['MATCH_OPTAUUID'] == m_id]
                
                # Hjælpefunktion til at hente specifik stat dynamisk
                def get_stat(team_name, stat_type):
                    val = match_stats[(match_stats['CONTESTANT_NAME'] == team_name) & 
                                     (match_stats['STAT_TYPE'] == stat_type)]['STAT_TOTAL'].sum()
                    return val

                # Dynamiske værdier
                h_xg = get_stat(h_name, 'expectedGoals')
                a_xg = get_stat(a_name, 'expectedGoals')
                h_pos = get_stat(h_name, 'possessionPercentage')
                a_pos = get_stat(a_name, 'possessionPercentage')
                h_shots = get_stat(h_name, 'totalShots')
                a_shots = get_stat(a_name, 'totalShots')

                # LAYOUT: Rå data uden ikoner
                c1, c2, c3 = st.columns([1, 2, 1])
                
                with c1:
                    st.metric("xG", f"{h_xg:.2f}")
                    st.write(f"Skud: {int(h_shots)}")
                
                with c2:
                    st.markdown(f"<p style='text-align:center; font-size:12px; margin-bottom:0;'>Boldbesiddelse %</p>", unsafe_allow_html=True)
                    # Progress bar baseret på rigtig possession
                    st.progress(float(h_pos)/100 if h_pos > 0 else 0.5)
                    st.markdown(f"<p style='text-align:center; font-size:11px;'>{h_pos}% - {a_pos}%</p>", unsafe_allow_html=True)
                
                with c3:
                    st.metric("xG", f"{a_xg:.2f}")
                    st.write(f"Skud: {int(a_shots)}")
                
                st.caption(f"🏟️ {row['VENUE_LONGNAME']} | Tilskuere: {int(row['ATTENDANCE']):,}")
            else:
                st.write(f"Kampen spilles på {row['VENUE_LONGNAME']}")
