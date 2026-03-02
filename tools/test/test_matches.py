import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())
    df_stats = dp.get("opta_team_stats", dp.get("team_stats_full", pd.DataFrame()))

    st.markdown("### 🏟️ Match Center: Tabeloversigt")

    # --- 1. FILTRE ---
    view_type = st.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'

    # --- 2. DATA BEHANDLING ---
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    matches = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=False)

    if matches.empty:
        st.info("Ingen kampe fundet.")
        return

    # --- 3. BYG TABEL-DATA ---
    tabel_data = []

    for _, row in matches.iterrows():
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        m_id = row['MATCH_OPTAUUID']
        
        # Hent stats for xG eller Besiddelse hvis de findes
        h_uuid = TEAMS.get(h_name, {}).get('opta_uuid')
        
        # Vi prøver at hente besiddelse som en hurtig stat til tabellen
        poss_val = 0
        if not df_stats.empty and h_uuid:
            p_stat = df_stats[(df_stats['MATCH_OPTAUUID'] == m_id) & 
                              (df_stats['CONTESTANT_OPTAUUID'] == h_uuid) & 
                              (df_stats['STAT_TYPE'] == 'possessionPercentage')]
            poss_val = pd.to_numeric(p_stat['STAT_TOTAL'], errors='coerce').max() if not p_stat.empty else 0

        entry = {
            "Dato": row['MATCH_DATE_FULL'].strftime("%d/%m") if hasattr(row['MATCH_DATE_FULL'], 'strftime') else "",
            "Hjemmehold": h_name,
            "Res": f"{int(row['TOTAL_HOME_SCORE'])} - {int(row['TOTAL_AWAY_SCORE'])}" if status_filter == 'Played' else "VS",
            "Udehold": a_name,
            "Besiddelse (H)": f"{poss_val:.0f}%" if poss_val > 0 else "-",
            "Stadion": row['VENUE_LONGNAME']
        }
        tabel_data.append(entry)

    # Lav til DataFrame
    df_vis = pd.DataFrame(tabel_data)

    # --- 4. VISNING ---
    # Vi bruger column_config for at gøre den interaktiv og pæn
    st.dataframe(
        df_vis,
        column_config={
            "Res": st.column_config.TextColumn("Resultat", help="Slutresultat"),
            "Besiddelse (H)": st.column_config.TextColumn("Poss %", help="Hjemmeholdets boldbesiddelse"),
            "Dato": st.column_config.TextColumn("Dato"),
        },
        hide_index=True,
        use_container_width=True
    )

    st.caption("💡 Tip: Du kan sortere tabellen ved at klikke på kolonnenavnene.")
