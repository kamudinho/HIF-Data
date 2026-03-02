import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", dp.get("team_stats_full", pd.DataFrame()))
    logos = dp.get("logo_map", {})

    # --- CSS: TOTAL FJERNELSE AF PIL + CENTRERING ---
    st.markdown("""
        <style>
        [data-testid="stExpander"] svg, [data-testid="stExpanderIcon"] { display: none !important; }
        [data-testid="stExpander"] summary p { 
            text-align: center !important; width: 100% !important; 
            font-weight: bold !important; font-size: 1.1rem !important; margin: 0 !important;
        }
        [data-testid="stExpander"] { border: none !important; background: transparent !important; }
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

    # --- 2. LOGIK ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    if valgt_hold != "Hele runden":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    if display_df.empty:
        st.info(f"Ingen {view_type.lower()} kampe fundet.")
        return

    # --- 3. VISNING ---
    for _, row in display_df.head(15).iterrows():
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        
        h_score = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_score = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
        score_text = f"{h_score} - {a_score}" if status_filter == 'Played' else "VS"

        col_l, col_m, col_r = st.columns([0.6, 4, 0.6])
        with col_l: 
            if h_name in logos: st.image(logos[h_name], width=35)
        with col_r: 
            if a_name in logos: st.image(logos[a_name], width=35)

        with col_m:
            with st.expander(f"{h_name}   {score_text}   {a_name}"):
                # --- ALT HERUNDER SKAL VÆRE INDRYKKET FOR AT VISES I EXPANDEREN ---
                h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')
                
                if status_filter == 'Played' and not df_stats.empty and h_uuid:
                    st.write("") 
                    
                    stats_list = [
                        ('totalScoringAtt', 'Skud total', False),
                        ('ontargetScoringAtt', 'Skud på mål', False),
                        ('wonCorners', 'Hjørnespark', False),
                        ('totalPass', 'Afleveringer', False),
                        ('possessionPercentage', 'Besiddelse %', True)
                    ]
                
                    for key, label, is_float in stats_list:
                        h_rows = df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & (df_stats['CONTESTANT_OPTAUUID'] == h_uuid) & (df_stats['STAT_TYPE'] == key)]
                        a_rows = df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & (df_stats['CONTESTANT_OPTAUUID'] == a_uuid) & (df_stats['STAT_TYPE'] == key)]
                        
                        h_val = pd.to_numeric(h_rows['STAT_TOTAL'], errors='coerce').sum() if not h_rows.empty else 0
                        a_val = pd.to_numeric(a_rows['STAT_TOTAL'], errors='coerce').sum() if not a_rows.empty else 0
                        
                        if key == 'possessionPercentage':
                            h_val = pd.to_numeric(h_rows['STAT_TOTAL'], errors='coerce').mean() if not h_rows.empty else 0
                            a_val = 100 - h_val if h_val > 0 else 0
                
                        fmt = "{:.1f}" if is_float else "{:.0f}"
                        
                        s1, s2, s3 = st.columns([1, 2, 1])
                        s1.markdown(f"<div class='stat-val'>{fmt.format(h_val)}</div>", unsafe_allow_html=True)
                        s2.markdown(f"<div class='stat-label'>{label}</div>", unsafe_allow_html=True)
                        s3.markdown(f"<div class='stat-val' style='text-align:right;'>{fmt.format(a_val)}</div>", unsafe_allow_html=True)
                else:
                    st.caption(f"🏟️ {row['VENUE_LONGNAME']} | Ingen detaljeret data fundet.")
        st.divider()
