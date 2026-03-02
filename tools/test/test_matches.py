import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", dp.get("team_stats_full", pd.DataFrame()))
    logos = dp.get("logo_map", {})

    # --- CSS: MODERNE MATCH CENTER LOOK ---
    st.markdown("""
        <style>
        .match-row {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 8px;
            margin-bottom: 5px;
        }
        .team-name { font-weight: 600; font-size: 1.1rem; }
        .score-box { 
            background: #333; color: white; padding: 5px 15px; 
            border-radius: 4px; font-weight: bold; margin: 0 20px;
            min-width: 60px; text-align: center;
        }
        [data-testid="stExpander"] { border: none !important; box-shadow: none !important; background: transparent !important; }
        [data-testid="stExpander"] svg { display: none !important; }
        .stat-label { text-align: center; color: gray; font-size: 11px; text-transform: uppercase; }
        .stat-val { font-weight: bold; font-size: 14px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🏟️ Match Center: 1. Division")

    # --- 1. FILTRE ---
    liga_hold = sorted([n for n, i in TEAMS.items() if i.get("league") in ["1. Division", "Betinia Ligaen"]])
    
    c_f1, c_f2 = st.columns([2, 1])
    with c_f1:
        valgt_hold = st.selectbox("Filtrer hold", ["Hele runden"] + liga_hold)
    with c_f2:
        view_type = st.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. DATA FILTRERING ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    if valgt_hold != "Hele runden":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    if display_df.empty:
        st.info(f"Ingen {view_type.lower()} kampe fundet.")
        return

    # --- 3. VISNING AF KAMPE ---
    for _, row in display_df.head(20).iterrows():
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        
        # Formatering af score/tid
        if status_filter == 'Played':
            h_score = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
            a_score = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
            mid_text = f"{h_score} - {a_score}"
        else:
            # Hvis kampen ikke er spillet, vis tidspunktet
            mid_text = row['MATCH_DATE_FULL'].strftime("%H:%M") if hasattr(row['MATCH_DATE_FULL'], 'strftime') else "VS"

        # Kamp-rækken
        with st.expander(f"{h_name}   {mid_text}   {a_name}"):
            # UUIDs til stats
            h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
            a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

            # Vis kun stats hvis kampen er spillet og vi har UUIDs
            if status_filter == 'Played' and h_uuid and a_uuid:
                stats_to_show = [
                    ('totalScoringAtt', 'Skud total'),
                    ('ontargetScoringAtt', 'Skud på mål'),
                    ('wonCorners', 'Hjørnespark'),
                    ('totalPass', 'Afleveringer'),
                    ('possessionPercentage', 'Besiddelse %')
                ]
                
                for key, label in stats_to_show:
                    h_rows = df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & (df_stats['CONTESTANT_OPTAUUID'] == h_uuid) & (df_stats['STAT_TYPE'] == key)]
                    a_rows = df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & (df_stats['CONTESTANT_OPTAUUID'] == a_uuid) & (df_stats['STAT_TYPE'] == key)]
                    
                    # Hent værdier
                    h_val = pd.to_numeric(h_rows['STAT_TOTAL'], errors='coerce').max() if not h_rows.empty else 0
                    a_val = pd.to_numeric(a_rows['STAT_TOTAL'], errors='coerce').max() if not a_rows.empty else 0
                    
                    if key == 'possessionPercentage' and h_val > 0 and a_val == 0:
                        a_val = 100 - h_val

                    # Vis rækken
                    s1, s2, s3 = st.columns([1, 2, 1])
                    s1.markdown(f"<div class='stat-val'>{h_val:g}</div>", unsafe_allow_html=True)
                    s2.markdown(f"<div class='stat-label'>{label}</div>", unsafe_allow_html=True)
                    s3.markdown(f"<div class='stat-val' style='text-align:right;'>{a_val:g}</div>", unsafe_allow_html=True)
            else:
                st.caption(f"🏟️ {row['VENUE_LONGNAME']} | Ingen kamp-statistik tilgængelig.")

    st.divider()
