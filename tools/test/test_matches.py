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
        /* Skjul pilen i alle versioner af Streamlit */
        [data-testid="stExpander"] svg, 
        [data-testid="stExpanderIcon"],
        .streamlit-expanderHeader svg { display: none !important; }
        
        /* Centrer teksten i expander-headeren */
        [data-testid="stExpander"] summary p { 
            text-align: center !important; 
            width: 100% !important; 
            font-weight: bold !important;
            font-size: 1.1rem !important;
            margin: 0 !important;
        }
        /* Gør expanderen flad og pæn */
        [data-testid="stExpander"] { border: none !important; background: transparent !important; }
        .stat-row { margin-bottom: 5px; border-bottom: 1px solid #f0f2f6; padding: 5px 0; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🏟️ Match Center: 1. Division")

    # --- 1. FILTRERING (Vi bruger liga-navnet fra Snowflake direkte) ---
    # Vi leder efter alt der minder om 1. division/Betinia/NordicBet i COMPETITION_NAME
    mask = df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False)
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=False)

    if display_df.empty:
        st.warning("Ingen data fundet. Tjek om 'opta_matches' er indlæst korrekt.")
        return

    # --- 2. LOOP GENNEM KAMPE ---
    for _, row in display_df.head(15).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        
        # Håndter scores (sikrer de er tal)
        h_score = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_score = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
        score_line = f"{h_score} - {a_score}"
        
        # Layout: Logo Venstre - Midte (Klikbar) - Logo Højre
        c_l, c_m, c_r = st.columns([0.6, 4, 0.6])
        
        with c_l:
            if logos.get(h_name): st.image(logos.get(h_name), width=35)
        with c_r:
            if logos.get(a_name): st.image(logos.get(a_name), width=35)

        with c_m:
            # Expander uden pil pga. CSS i toppen
            with st.expander(f"{h_name}   {score_line}   {a_name}"):
                
                # Find Opta UUIDs i din TEAMS mapping
                h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

                if h_uuid and a_uuid and not df_stats.empty:
                    # Funktion til at hente stats sikkert
                    def get_stat(t_uuid, s_type):
                        val = df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                                      (df_stats['CONTESTANT_OPTAUUID'] == t_uuid) & 
                                      (df_stats['STAT_TYPE'] == s_type)]['STAT_TOTAL'].sum()
                        return val

                    # Visning af stats i rækker
                    stats_list = [
                        ('expectedGoals', 'xG', True),
                        ('totalShots', 'SKUD', False),
                        ('shotsOnTarget', 'SKUD PÅ MÅL', False),
                        ('bigChancesTotal', 'STORE CHANCER', False),
                        ('possessionPercentage', 'BESIDDELSE %', False)
                    ]

                    st.write("") # Luft
                    for key, label, is_float in stats_list:
                        s1, s2, s3 = st.columns([1, 2, 1])
                        h_val = get_stat(h_uuid, key)
                        a_val = get_stat(a_uuid, key)
                        
                        fmt = "{:.2f}" if is_float else "{:.0f}"
                        
                        s1.markdown(f"**{fmt.format(h_val)}**")
                        s2.markdown(f"<p style='text-align:center; color:gray; font-size:12px;'>{label}</p>", unsafe_allow_html=True)
                        s3.markdown(f"<div style='text-align:right;'>**{fmt.format(a_val)}**</div>", unsafe_allow_html=True)
                else:
                    st.caption(f"🏟️ {row['VENUE_LONGNAME']} | Ingen detaljeret Opta-data endnu.")
        
        st.divider()
