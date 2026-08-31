import streamlit as st
import pandas as pd
from utils.positional_helper import beregn_primaere_positioner

def vis_side(advanced_stats_df, position_base_df=None):
    st.markdown("### Top 10 Scouting – Divisioner", unsafe_allow_html=True)
    
    if advanced_stats_df is None or advanced_stats_df.empty:
        st.warning("Ingen avanceret statistik tilgængelig.")
        return

    # Sørg for at kolonnenavne er uppercase for sikkerhed
    df = advanced_stats_df.copy()
    df.columns = [c.upper().strip() for c in df.columns]

    # Beregn primære positioner hvis position_base_df er medsendt
    if position_base_df is not None and not position_base_df.empty:
        primaer_pos_df = beregn_primaere_positioner(position_base_df)
        if not primaer_pos_df.empty:
            primaer_pos_df.columns = [c.upper().strip() for c in primaer_pos_df.columns]
            # Merge pos_group og position ind på advanced_stats baseret på spiller ID
            id_col_adv = next((c for c in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID'] if c in df.columns), None)
            id_col_pos = next((c for c in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID'] if c in primaer_pos_df.columns), None)
            
            if id_col_adv and id_col_pos:
                df['TEMP_ID'] = df[id_col_adv].astype(str).str.split('.').str[0].str.strip()
                primaer_pos_df['TEMP_ID'] = primaer_pos_df[id_col_pos].astype(str).str.split('.').str[0].str.strip()
                df = df.merge(primaer_pos_df[['TEMP_ID', 'POS_GROUP', 'POSITION']], on='TEMP_ID', how='left')

    # Tjek om positionsgruppe / position findes
    pos_col = 'POS_GROUP' if 'POS_GROUP' in df.columns else ('POS_GRUPPE' if 'POS_GRUPPE' in df.columns else None)
    if not pos_col:
        st.error("Kunne ikke finde positionsgrupper. Kør venligst positional_helper først.")
        return

    # Hent mulige positioner/grupper til dropdown
    mulige_grupper = sorted([g for g in df[pos_col].dropna().unique() if g != "Ukendt"])
    if not mulige_grupper:
        st.info("Ingen gyldige positionsgrupper fundet i data.")
        return

    valgt_gruppe = st.selectbox("Vælg Positionsgruppe", mulige_grupper)

    # 1. division (328), 2. division (329), 3. division (43319 - bemærk 43319 ifølge din spec)
    liga_mapping = {
        328: "1. Division",
        329: "2. Division",
        43319: "3. Division"
    }

    # Tjek hvilken kolonne der indeholder liga/competition ID
    komp_col = next((c for c in ['COMPETITION_WYID', 'COMPETITION_ID', 'LEAGUE_ID', 'COMP_ID'] if c in df.columns), None)
    
    col1, col2, col3 = st.columns(3)
    kolonner = [col1, col2, col3]

    # Relevante metrics per positionsgruppe (eksempler på summering pr. 90)
    # Du kan tilpasse disse lister alt efter hvilke kolonner der findes i dine advanced stats
    metrik_mapping = {
        "Angriber": ["GOALS P90", "SHOTS P90", "TOUCHESINBOX P90", "EXPECTEDGOALS P90"],
        "Kant": ["ASSISTS P90", "CROSSESVALUABLE P90", "DRIBBLES P90", "KEYPASSES P90"],
        "Central Midtbane": ["PASSESACCURATE P90", "RECOVERIES P90", "DUELSWON P90", "KEYPASSES P90"],
        "Forsvarer": ["DUELSWON P90", "INTERCEPTIONS P90", "CLEARANCES P90", "AERIALDUELSWON P90"],
        "Målmand": ["SAVES P90", "PREVENTEDGOALS P90"]
    }

    # Standard fallback hvis gruppen ikke er i mappingen
    aktive_metrikker = metrik_mapping.get(valgt_gruppe, ["PASSESACCURATE P90", "DUELSWON P90"])

    for idx, (komp_id, liga_navn) in enumerate(liga_mapping.items()):
        with kolonner[idx]:
            st.markdown(f"#### {liga_navn}")

            if not komp_col:
                st.error("Kunne ikke finde turnering-kolonne i data.")
                continue

            # Filtrer på liga og positionsgruppe
            liga_df = df[(df[komp_col].astype(str).str.contains(str(komp_id))) & (df[pos_col] == valgt_gruppe)].copy()

            if liga_df.empty:
                st.info("Ingen spillere fundet.")
                continue

            # Find faktiske kolonner der matcher de ønskede metrikker (case-insensitive tjek)
            Eksisterende_metrikker = []
            for m in aktive_metrikker:
                match_col = next((c for c in liga_df.columns if m.replace(" ", "") in c.replace(" ", "")), None)
                if match_col:
                    Eksisterende_metrikker.append(match_col)

            if not Eksisterende_metrikker:
                # Fallback: Find alle numeriske kolonner der ender på P90 hvis specifikke ikke findes
                Eksisterende_metrikker = [c for c in liga_df.select_dtypes(include=['number']).columns if 'P90' in c][:3]

            if not Eksisterende_metrikker:
                st.info("Ingen relevante metrics fundet.")
                continue

            # Beregn samlet score (simpelt gennemsnit eller sum af de valgte P90-tal)
            liga_df['SCORE'] = 0
            for m in Eksisterende_metrikker:
                liga_df[m] = pd.to_numeric(liga_df[m], errors='fillna').fillna(0)
                liga_df['SCORE'] += liga_df[m]

            # Sorter og tag top 10
            top10 = liga_df.sort_values(by='SCORE', ascending=False).head(10)

            navn_col = next((c for c in ['PLAYERNAME', 'NAVN', 'PLAYER_NAME', 'NAME'] if c in top10.columns), top10.columns[0])
            hold_col = next((c for c in ['TEAMNAME', 'KLUB', 'TEAM_NAME'] if c in top10.columns), None)

            # Vis som en ren og pæn tabel/liste
            for i, (_, row) in enumerate(top10.iterrows(), 1):
                p_navn = row.get(navn_col, "Ukendt")
                p_hold = row.get(hold_col, "") if hold_col else ""
                p_score = round(row.get('SCORE', 0), 2)
                
                st.markdown(f"""
                    <div style='padding: 8px 10px; margin-bottom: 6px; background: #fff; border: 1px solid #eee; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;'>
                        <div>
                            <span style='font-weight: bold; color: #df003b; margin-right: 6px;'>{i}.</span> 
                            <span style='font-weight: 600; font-size: 0.9rem;'>{p_navn}</span><br>
                            <span style='font-size: 0.75rem; color: gray;'>{p_hold}</span>
                        </div>
                        <div style='text-align: right;'>
                            <span style='font-weight: 800; font-size: 0.95rem;'>{p_score}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
