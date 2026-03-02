import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS, COMPETITIONS

def vis_side():
    dp = st.session_state.get("dp")
    # Vi henter dataen - og sikrer os de er der
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})
    
    st.markdown("### 🏟️ Match Center: Betinia Ligaen")

    # --- 1. FILTER: Kun hold fra Betinia Ligaen ---
    # Vi filtrerer TEAMS listen så vi kun får dem der hører til Betinia Ligaen
    liga_hold = [navn for navn, info in TEAMS.items() if info.get("league") == "Betinia Ligaen"]
    liga_hold = sorted(liga_hold)

    col1, col2 = st.columns([2, 1])
    # Vi tilføjer "Alle hold" (i 1. div) som default
    valgt_hold = col1.selectbox("Filtrer hold i 1. division", ["Hele runden"] + liga_hold)
    view_type = col2.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. LOGIK: Filtrering på liga-navnet fra din Snowflake query ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    
    # Vi sikrer os at vi kun ser kampe fra Betinia Ligaen (NordicBet Liga)
    # Vi bruger navnet direkte som det optræder i din Snowflake-tabel
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    if valgt_hold != "Hele runden":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- 3. VISNING ---
    if display_df.empty:
        st.info("Ingen kampe fundet for den valgte filtrering.")
        return

    for _, row in display_df.head(15).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        h_logo = logos.get(h_name)
        m_id = row['MATCH_OPTAUUID']
        
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # Kompakt Expander med logo
        with st.expander(f"{h_name}  {score}  {a_name}", icon=h_logo):
            if status_filter == 'Played' and not df_stats.empty:
                # Find UUIDs fra din mapping til præcist data-opslag
                h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

                # Dynamisk stat-hentning (Uden hardkodning)
                def get_s(t_uuid, s_type):
                    return df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                                    (df_stats['CONTESTANT_OPTAUUID'] == t_uuid) & 
                                    (df_stats['STAT_TYPE'] == s_type)]['STAT_TOTAL'].sum()

                # Visning af rå data
                c1, c2, c3 = st.columns([1, 1, 1])
                c1.metric("xG", f"{get_s(h_uuid, 'expectedGoals'):.2f}")
                
                with c2:
                    pos = get_s(h_uuid, 'possessionPercentage')
                    st.markdown(f"<p style='text-align:center;font-size:12px;margin-bottom:2px;'>Possession</p>", unsafe_allow_html=True)
                    st.progress(float(pos)/100 if pos else 0.5)
                    st.markdown(f"<p style='text-align:center;font-size:11px;'>{pos}% - {100-pos if pos else 50}%</p>", unsafe_allow_html=True)
                
                c3.write(f"<p style='text-align:right;'><b>xG</b><br>{get_s(a_uuid, 'expectedGoals'):.2f}</p>", unsafe_allow_html=True)
            else:
                st.write(f"🏟️ {row['VENUE_LONGNAME']} | {row['MATCH_DATE_FULL'].strftime('%d/%m kl. %H:%M')}")
