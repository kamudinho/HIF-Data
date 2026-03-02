import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp")
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", pd.DataFrame())
    logos = dp.get("logo_map", {})

    # --- CSS: Fjerner expander-pil og centrerer titlen ---
    st.markdown("""
        <style>
        /* Skjul pilen (chevron) */
        [data-testid="stExpanderDetails"] summary svg {
            display: none !important;
        }
        /* Centrer teksten i expander-headeren */
        [data-testid="stExpanderDetails"] summary p {
            text-align: center !important;
            width: 100%;
            font-weight: bold;
            font-size: 1.1rem;
        }
        /* Fjern unødvendig luft */
        .stElementContainer div[data-testid="stExpander"] {
            border: none !important;
            border-bottom: 1px solid #333 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🏟️ Match Center: 1. Division")

    # --- 1. FILTER ---
    liga_hold = [navn for navn, info in TEAMS.items() if info.get("league") == "Betinia Ligaen"]
    valgt_hold = st.selectbox("Filtrer hold", ["Hele runden"] + sorted(liga_hold))
    view_type = st.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")

    # --- 2. LOGIK ---
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    if valgt_hold != "Hele runden":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
    display_df = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=(status_filter == 'Fixture'))

    # --- 3. VISNING ---
    for _, row in display_df.head(15).iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        score = f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS"
        
        # Titlen der nu bliver centreret via CSS
        expander_label = f"{h_name}   {score}   {a_name}"
        
        with st.expander(expander_label):
            # Header inde i expanderen med LOGOER
            c_header = st.columns([1, 4, 1])
            with c_header[0]:
                if logos.get(h_name): st.image(logos.get(h_name), width=40)
            with c_header[1]:
                st.markdown(f"<p style='text-align:center; color:gray; font-size:12px;'>{row['VENUE_LONGNAME']}<br>{row['MATCH_DATE_FULL'].strftime('%d. %b kl. %H:%M')}</p>", unsafe_allow_html=True)
            with c_header[2]:
                # Højre-justeret logo til udeholdet
                if logos.get(a_name): 
                    st.markdown(f"<div style='text-align:right;'><img src='{logos.get(a_name)}' width='40'></div>", unsafe_allow_html=True)
            
            st.divider()

            # --- OPTA DATA ---
            if status_filter == 'Played' and not df_stats.empty:
                h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
                a_uuid = TEAMS.get(a_name, {}).get('opta_uuid')

                def get_s(t_uuid, s_type):
                    return df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                                    (df_stats['CONTESTANT_OPTAUUID'] == t_uuid) & 
                                    (df_stats['STAT_TYPE'] == s_type)]['STAT_TOTAL'].sum()

                # Data-layout (Ingen ikoner, råt udtryk)
                d1, d2, d3 = st.columns([1, 1, 1])
                d1.metric("xG", f"{get_s(h_uuid, 'expectedGoals'):.2f}")
                
                with d2:
                    pos = get_s(h_uuid, 'possessionPercentage')
                    st.markdown("<p style='text-align:center; font-size:11px; margin-bottom:0;'>Possession</p>", unsafe_allow_html=True)
                    st.progress(float(pos)/100 if pos else 0.5)
                    st.markdown(f"<p style='text-align:center; font-size:10px;'>{pos}% - {100-pos if pos else 50}%</p>", unsafe_allow_html=True)

                d3.write(f"<div style='text-align:right;'><b>xG</b><br>{get_s(a_uuid, 'expectedGoals'):.2f}</div>", unsafe_allow_html=True)
