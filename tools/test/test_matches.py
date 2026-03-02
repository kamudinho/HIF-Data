import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp")
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})

    # --- CSS: INGEN PIL, CENTRERET OG STRAMT ---
    st.markdown("""
        <style>
        [data-testid="stExpander"] svg { display: none !important; }
        [data-testid="stExpander"] summary p { 
            text-align: center !important; 
            width: 100% !important; 
            font-weight: bold !important;
            font-size: 1.1rem !important;
        }
        [data-testid="stExpander"] { border: none !important; }
        </style>
    """, unsafe_allow_html=True)

    # 1. FILTRERING (Kun Betinia Ligaen)
    tilladte_hold = [n for n, i in TEAMS.items() if i.get("league") == "Betinia Ligaen"]
    mask = (df_matches['CONTESTANTHOME_NAME'].isin(tilladte_hold)) & \
           (df_matches['CONTESTANTAWAY_NAME'].isin(tilladte_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=False)

    for _, row in display_df.head(10).iterrows():
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}"
        
        c_l, c_m, c_r = st.columns([0.6, 4, 0.6])
        with c_l: st.image(logos.get(h_name, ""), width=35)
        with c_r: st.image(logos.get(a_name, ""), width=35)

        with c_m:
            with st.expander(f"{h_name}   {score}   {a_name}"):
                # --- HER ER DIN NYE RÅ OVERSIGT ---
                h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

                def get_s(t_uuid, s_type):
                    val = df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                                  (df_stats['CONTESTANT_OPTAUUID'] == t_uuid) & 
                                  (df_stats['STAT_TYPE'] == s_type)]['STAT_TOTAL'].sum()
                    return val

                # Rå data-sammenligning uden dikkedarer
                # Vi bruger kolonner til at lave en "tabel" manuelt
                col_left, col_mid, col_right = st.columns([1, 1, 1])
                
                stats_to_show = [
                    ('expectedGoals', 'xG'),
                    ('totalShots', 'Skud'),
                    ('shotsOnTarget', 'Skud på mål'),
                    ('bigChancesTotal', 'Store chancer'),
                    ('possessionPercentage', 'Boldbesiddelse %')
                ]

                for opta_key, label in stats_to_show:
                    h_val = get_s(h_uuid, opta_key)
                    a_val = get_s(a_uuid, opta_key)
                    
                    # Formatering (hvis det er xG, vis 2 decimaler)
                    fmt = ".2f" if "expected" in opta_key else ".0f"
                    
                    with col_left: st.write(f"{h_val:{fmt}}")
                    with col_mid: st.markdown(f"<p style='text-align:center; color:gray; font-size:12px;'>{label}</p>", unsafe_allow_html=True)
                    with col_right: st.markdown(f"<p style='text-align:right;'>{a_val:{fmt}}</p>", unsafe_allow_html=True)
                
                st.caption(f"🏟️ {row['VENUE_LONGNAME']}")
        st.divider()
