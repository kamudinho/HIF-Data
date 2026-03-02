import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp")
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})

    # --- CSS: TOTAL FJERNELSE AF PIL + CENTRERING ---
    st.markdown("""
        <style>
        [data-testid="stExpander"] svg { display: none !important; }
        [data-testid="stExpander"] summary p { 
            text-align: center !important; 
            width: 100% !important; 
            font-weight: bold !important;
            font-size: 1.1rem !important;
        }
        [data-testid="stExpander"] { border: none !important; margin-bottom: -15px; }
        .stat-label { text-align: center; color: gray; font-size: 13px; font-weight: 500; }
        .stat-val { font-weight: bold; font-size: 15px; }
        </style>
    """, unsafe_allow_html=True)

    # 1. SMART FILTRERING (Vi inkluderer Hvidovre uanset stavemåde)
    # Vi tjekker om ligaen er 1. Division (som defineret i din VALGT_LIGA)
    mask = df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False)
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=False)

    if display_df.empty:
        st.info("Ingen kampe fundet i 1. Division.")
        return

    for _, row in display_df.head(15).iterrows():
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        
        # Håndtering af manglende scores (hvis kampen ikke er spillet)
        h_score = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_score = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
        score_text = f"{h_score} - {a_score}"
        
        # Layout: Logo - Navne/Score - Logo
        c_l, c_m, c_r = st.columns([0.6, 4, 0.6])
        with c_l: st.image(logos.get(h_name, ""), width=35)
        with c_r: st.image(logos.get(a_name, ""), width=35)

        with c_m:
            # Expander titlen fungerer nu som din centreret knap
            with st.expander(f"{h_name}   {score_text}   {a_name}"):
                
                # Hent UUIDs (Sørg for at din TEAMS mapping har både "Hvidovre" og "Hvidovre IF")
                h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

                if h_uuid and a_uuid and not df_stats.empty:
                    st.write("") # Spacer
                    
                    stats_to_show = [
                        ('expectedGoals', 'EXPECTED GOALS (xG)', True),
                        ('totalShots', 'SKUD', False),
                        ('shotsOnTarget', 'SKUD PÅ MÅL', False),
                        ('bigChancesTotal', 'STORE CHANCER', False),
                        ('possessionPercentage', 'BOLD BESIDDELSE %', False)
                    ]

                    for opta_key, label, is_float in stats_to_show:
                        # Lokal get_s funktion
                        def get_val(t_uuid, key):
                            val = df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                                          (df_stats['CONTESTANT_OPTAUUID'] == t_uuid) & 
                                          (df_stats['STAT_TYPE'] == key)]['STAT_TOTAL'].sum()
                            return val

                        h_val = get_val(h_uuid, opta_key)
                        a_val = get_val(a_uuid, opta_key)
                        
                        # Tabel-række layout
                        s1, s2, s3 = st.columns([1, 2, 1])
                        val_str = "{:.2f}" if is_float else "{:.0f}"
                        
                        s1.markdown(f"<div class='stat-val'>{val_str.format(h_val)}</div>", unsafe_allow_html=True)
                        s2.markdown(f"<div class='stat-label'>{label}</div>", unsafe_allow_html=True)
                        s3.markdown(f"<div class='stat-val' style='text-align:right;'>{val_str.format(a_val)}</div>", unsafe_allow_html=True)
                else:
                    st.caption(f"📍 {row['VENUE_LONGNAME']} | Ingen detaljeret Opta-data endnu.")
        
        st.divider()
