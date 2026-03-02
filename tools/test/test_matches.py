import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp")
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})

    # CSS til at fjerne pilen og gøre expanderen usynlig i kanten
    st.markdown("""
        <style>
        [data-testid="stExpanderDetails"] summary svg { display: none !important; }
        [data-testid="stExpanderDetails"] { border: none !important; box-shadow: none !important; }
        [data-testid="stExpanderDetails"] summary p { text-align: center !important; font-weight: bold; }
        .stExpander { border: none !important; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🏟️ Match Center: 1. Division")

    # --- LOGIK & FILTRERING ---
    liga_hold = [navn for navn, info in TEAMS.items() if info.get("league") == "Betinia Ligaen"]
    valgt_hold = st.selectbox("Filtrer hold", ["Hele runden"] + sorted(liga_hold))
    view_type = st.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    if valgt_hold != "Hele runden":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- VISNING ---
    for _, row in display_df.head(15).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # HER SNYDER VI: Vi laver 3 kolonner. Logo - Expander (Tekst) - Logo
        col_logo_h, col_main, col_logo_a = st.columns([0.5, 4, 0.5])
        
        with col_logo_h:
            if logos.get(h_name): st.image(logos.get(h_name), width=35)
        
        with col_logo_a:
            if logos.get(a_name): st.image(logos.get(a_name), width=35)

        with col_main:
            # Expander titlen er nu KUN resultatet, centreret mellem logoerne
            with st.expander(f"{h_name}  {score}  {a_name}"):
                # --- INDHOLD (KUN DATA) ---
                if status_filter == 'Played' and not df_stats.empty:
                    h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                    a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

                    def get_s(t_uuid, s_type):
                        return df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                                        (df_stats['CONTESTANT_OPTAUUID'] == t_uuid) & 
                                        (df_stats['STAT_TYPE'] == s_type)]['STAT_TOTAL'].sum()

                    d1, d2, d3 = st.columns([1, 1, 1])
                    d1.metric("xG", f"{get_s(h_uuid, 'expectedGoals'):.2f}")
                    with d2:
                        pos = get_s(h_uuid, 'possessionPercentage')
                        st.markdown("<p style='text-align:center;font-size:11px;'>Possession</p>", unsafe_allow_html=True)
                        st.progress(float(pos)/100 if pos else 0.5)
                    d3.write(f"<div style='text-align:right;'><b>xG</b><br>{get_s(a_uuid, 'expectedGoals'):.2f}</div>", unsafe_allow_html=True)
                else:
                    st.caption(f"🏟️ {row['VENUE_LONGNAME']} | {row['MATCH_DATE_FULL'].strftime('%d. %b kl. %H:%M')}")
        
        st.divider() # En tynd linje mellem kampene
