import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side():
    dp = st.session_state.get("dp", {})
    df_matches = dp.get("opta_matches", pd.DataFrame())

    # --- 2. FARVER & KONSTANTER (Nu korrekt indrykket) ---
    hif_rod = "#df003b"

    # --- TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:1px; border-radius:1px; margin-bottom:1px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">BETINIA LIGAEN: KAMPOVERSIGT</h3>
        </div>
    """, unsafe_allow_html=True)

    # --- 1. FILTRE ---
    # Hent alle hold fra 1. Division til dropdown
    liga_hold = sorted([n for n, i in TEAMS.items() if i.get("league") in ["1. Division", "Betinia Ligaen", "NordicBet Liga"]])
    
    c_f1, c_f2 = st.columns([2, 1])
    with c_f1:
        valgt_hold = st.selectbox("Vælg hold", ["Hele runden"] + liga_hold)
    with c_f2:
        view_type = st.segmented_control("Status", ["Spillede", "Kommende"], default="Spillede")
    
    status_filter = 'Played' if view_type == "Spillede" else 'Fixture'

    # --- 2. DATA BEHANDLING ---
    mask = (df_matches['MATCH_STATUS'] == status_filter) & \
           (df_matches['COMPETITION_NAME'].str.contains('1. Division|NordicBet|Betinia', case=False, na=False))
    
    # Tilføj hold-filtrering hvis valgt
    if valgt_hold != "Hele runden":
        mask = mask & ((df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold))
    
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
        kamp_tekst = f"{h_name} vs. {a_name}"
        dato_str = row['MATCH_DATE_FULL'].strftime("%d/%m") if hasattr(row['MATCH_DATE_FULL'], 'strftime') else ""

        if status_filter == 'Played':
            h_score = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
            a_score = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
            res_tekst = f"{h_score} - {a_score}"
        else:
            res_tekst = row['MATCH_DATE_FULL'].strftime("%H:%M") if hasattr(row['MATCH_DATE_FULL'], 'strftime') else "VS"

        tabel_rows.append({
            "Dato": dato_str,
            "Kamp": kamp_tekst,
            "Resultat": res_tekst
        })

    df_vis = pd.DataFrame(tabel_rows)

    # --- 4. VISNING ---
    # Vi beregner højden dynamisk (ca. 35 pixels per række + lidt til header)
    calc_height = (len(df_vis) + 1) * 35 + 3

    st.dataframe(
        df_vis,
        column_config={
            "Dato": st.column_config.TextColumn("Dato", width="small"),
            "Kamp": st.column_config.TextColumn("Kamp", width="large"),
            "Resultat": st.column_config.TextColumn("Res", width="small"),
        },
        hide_index=True,
        use_container_width=True,
        height=calc_height # Dette fjerner scroll-baren og viser alle rækker
    )

    st.divider()
