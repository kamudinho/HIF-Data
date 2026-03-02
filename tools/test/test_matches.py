import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp")
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})

    # --- CSS: FJERNER PILEN OG STYLER TITLEN ---
    st.markdown("""
        <style>
        /* Skjul pilen (chevron) i expanderen */
        [data-testid="stExpander"] summary svg {
            display: none !important;
        }
        /* Fjern rammen omkring expander-titlen for et renere look */
        [data-testid="stExpander"] {
            border: none !important;
            background-color: transparent !important;
        }
        /* Centrer teksten i expander-titlen */
        [data-testid="stExpander"] summary p {
            text-align: center !important;
            font-weight: bold;
            font-size: 1.1rem;
            margin: 0 !important;
        }
        /* Gør overskriften klikbar over det hele */
        [data-testid="stExpander"] summary {
            padding: 10px 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🏟️ Match Center: 1. Division")

    # --- FILTRERING ---
    liga_hold = [navn for navn, info in TEAMS.items() if info.get("league") == "Betinia Ligaen"]
    valgt_hold = st.selectbox("Filtrer hold", ["Hele runden"] + sorted(liga_hold))
    view_type = st.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    if valgt_hold != "Hele runden":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- VISNING AF RÆKKER ---
    for _, row in display_df.head(15).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # Vi bruger kolonner til at vise logoer UDENOM expanderen
        # Dette sikrer at logoerne altid er der, og midten er klikbar
        col_l, col_m, col_r = st.columns([0.6, 4, 0.6])
        
        with col_l:
            logo_h = logos.get(h_name)
            if logo_h: st.image(logo_h, width=35)
            
        with col_r:
            logo_a = logos.get(a_name)
            if logo_a: st.image(logo_a, width=35)

        with col_m:
            # Expander uden pil pga. CSS'en i toppen
            with st.expander(f"{h_name}  {score}  {a_name}"):
                if status_filter == 'Played' and not df_stats.empty:
                    # Opta data opslag
                    h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                    a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

                    def get_s(t_uuid, s_type):
                        return df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                                        (df_stats['CONTESTANT_OPTAUUID'] == t_uuid) & 
                                        (df_stats['STAT_TYPE'] == s_type)]['STAT_TOTAL'].sum()

                    # Rå data-visning (Ingen ikoner)
                    d1, d2, d3 = st.columns([1, 1, 1])
                    d1.metric("xG", f"{get_s(h_uuid, 'expectedGoals'):.2f}")
                    with d2:
                        pos = get_s(h_uuid, 'possessionPercentage')
                        st.markdown("<p style='text-align:center;font-size:11px;'>Possession</p>", unsafe_allow_html=True)
                        st.progress(float(pos)/100 if pos else 0.5)
                    d3.write(f"<div style='text-align:right;'><b>xG</b><br>{get_s(a_uuid, 'expectedGoals'):.2f}</div>", unsafe_allow_html=True)
                else:
                    st.caption(f"🏟️ {row['VENUE_LONGNAME']} | {row['MATCH_DATE_FULL'].strftime('%d. %b kl. %H:%M')}")
        
        st.divider()
