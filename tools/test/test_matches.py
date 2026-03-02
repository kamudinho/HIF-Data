import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp")
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})

    # --- CSS: TOTAL FJERNELSE AF PIL OG CENTRERING ---
    st.markdown("""
        <style>
        /* Fjern pilen uanset hvor Streamlit gemmer den */
        [data-testid="stExpander"] summary svg, 
        [data-testid="stExpander"] summary span svg,
        [data-testid="stHeaderActionElements"] {
            display: none !important;
        }
        /* Centrer teksten og fjern polstring så det flugter med logoer */
        [data-testid="stExpander"] summary p {
            text-align: center !important;
            width: 100% !important;
            font-weight: bold !important;
            font-size: 1.1rem !important;
        }
        /* Gør selve expander-baren flad og professionel */
        [data-testid="stExpander"] {
            border: none !important;
            background: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🏟️ Match Center: 1. Division")

    # --- 1. STRIKT FILTRERING: Kun Betinia Ligaen ---
    # Vi laver en liste over holdnavne der MÅ vises (kun dem fra Betinia Ligaen)
    tilladte_hold = [navn for navn, info in TEAMS.items() if info.get("league") == "Betinia Ligaen"]
    
    valgt_hold = st.selectbox("Filtrer hold", ["Hele runden"] + sorted(tilladte_hold))
    view_type = st.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. LOGIK ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    
    # Maske der KUN tillader kampe hvor BEGGE hold findes i vores 1. div liste
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['CONTESTANTHOME_NAME'].isin(tilladte_hold)) & \
           (df_matches['CONTESTANTAWAY_NAME'].isin(tilladte_hold))
    
    if valgt_hold != "Hele runden":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- 3. VISNING ---
    for _, row in display_df.head(15).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # Kolonner for at centrere expanderen mellem logoerne
        col_l, col_m, col_r = st.columns([0.6, 4, 0.6])
        
        with col_l:
            if logos.get(h_name): st.image(logos.get(h_name), width=35)
        with col_r:
            if logos.get(a_name): st.image(logos.get(a_name), width=35)

        with col_m:
            # Expander titlen er nu centreret og uden pil
            with st.expander(f"{h_name}   {score}   {a_name}"):
                # Herinde viser vi dataen råt
                if status_filter == 'Played' and not df_stats.empty:
                    h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                    a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

                    def get_s(t_uuid, s_type):
                        return df_stats[(df_stats['MATCH_OPTAUUID'] == row['MATCH_OPTAUUID']) & 
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
        
        st.divider()
