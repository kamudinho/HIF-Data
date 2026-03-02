import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())

    st.markdown("### 🏟️ Match Center: 1. Division")

    # --- 1. FILTRE ---
    view_type = st.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'

    # --- 2. DATA BEHANDLING ---
    # Filtrer på liga (NordicBet Liga / 1. Division) og status
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    # Sortér: Nyeste kampe øverst for spillede, kommende kampe i dato-orden
    sort_order = False if status_filter == 'Played' else True
    matches = df_matches[mask].sort_values('MATCH_DATE_FULL', ascending=sort_order)

    if matches.empty:
        st.info(f"Ingen {view_type.lower()} kampe fundet.")
        return

    # --- 3. BYG TABEL-DATA ---
    tabel_rows = []

    for _, row in matches.iterrows():
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        
        # Merge holdene til "Kamp"
        kamp_tekst = f"{h_name} vs. {a_name}"
        
        # Formater dato (f.eks. 02/03)
        dato_str = row['MATCH_DATE_FULL'].strftime("%d/%m") if hasattr(row['MATCH_DATE_FULL'], 'strftime') else ""

        # Håndter resultat eller tidspunkt
        if status_filter == 'Played':
            h_score = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
            a_score = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
            res_tekst = f"{h_score} - {a_score}"
        else:
            # Vis klokkeslæt for kommende kampe
            res_tekst = row['MATCH_DATE_FULL'].strftime("%H:%M") if hasattr(row['MATCH_DATE_FULL'], 'strftime') else "VS"

        tabel_rows.append({
            "Dato": dato_str,
            "Kamp": kamp_tekst,
            "Resultat": res_tekst
        })

    # Lav til DataFrame
    df_vis = pd.DataFrame(tabel_rows)

    # --- 4. VISNING ---
    st.dataframe(
        df_vis,
        column_config={
            "Dato": st.column_config.TextColumn("Dato", width="small"),
            "Kamp": st.column_config.TextColumn("Kamp", width="large"),
            "Resultat": st.column_config.TextColumn("Res", width="small"),
        },
        hide_index=True,
        use_container_width=True
    )

    st.divider()
