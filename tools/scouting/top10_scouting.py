import streamlit as st
import pandas as pd
from utils.positional_helper import beregn_primaere_positioner

def vis_side(advanced_stats_df, position_base_df=None):
    st.markdown("### Top 10 Scouting – Divisioner", unsafe_allow_html=True)
    
    if advanced_stats_df is None or advanced_stats_df.empty:
        st.warning("Ingen avanceret statistik tilgængelig.")
        return

    df = advanced_stats_df.copy()
    df.columns = [c.upper().strip() for c in df.columns]

    if position_base_df is not None and not position_base_df.empty:
        primaer_pos_df = beregn_primaere_positioner(position_base_df)
        if not primaer_pos_df.empty:
            primaer_pos_df.columns = [c.upper().strip() for c in primaer_pos_df.columns]
            id_col_adv = next((c for c in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID'] if c in df.columns), None)
            id_col_pos = next((c for c in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID'] if c in primaer_pos_df.columns), None)
            
            if id_col_adv and id_col_pos:
                df['TEMP_ID'] = df[id_col_adv].astype(str).str.split('.').str[0].str.strip()
                primaer_pos_df['TEMP_ID'] = primaer_pos_df[id_col_pos].astype(str).str.split('.').str[0].str.strip()
                df = df.merge(primaer_pos_df[['TEMP_ID', 'PRIMAER_POSITIONSGRUPPE']], on='TEMP_ID', how='left')
                df = df.rename(columns={'PRIMAER_POSITIONSGRUPPE': 'POS_GROUP'})

    pos_col = 'POS_GROUP' if 'POS_GROUP' in df.columns else ('POS_GRUPPE' if 'POS_GRUPPE' in df.columns else None)
    if not pos_col:
        st.error("Kunne ikke finde positionsgrupper. Sørg for at position_base_df (WYSCOUT_PLAYERADVANCEDSTATS_BASE) sendes med til siden.")
        return

    mulige_grupper = sorted([g for g in df[pos_col].dropna().unique() if g != "Ukendt"])
    if not mulige_grupper:
        st.info("Ingen gyldige positionsgrupper fundet i data.")
        return

    valgt_gruppe = st.selectbox("Vælg Positionsgruppe", mulige_grupper)

    liga_mapping = {
        328: "1. Division",
        329: "2. Division",
        43149: "3. Division"
    }

    komp_col = next((c for c in ['COMPETITION_WYID', 'COMPETITION_ID', 'LEAGUE_ID', 'COMP_ID'] if c in df.columns), None)
    
    col1, col2, col3 = st.columns(3)
    kolonner = [col1, col2, col3]

    metrik_mapping = {
        "Angriber": ["GOALS", "SHOTS", "TOUCHINBOX", "XGSHOT"],
        "Kant": ["ASSISTS", "SUCCESSFULCROSSES", "SUCCESSFULDRIBBLES", "KEYPASSES"],
        "Central Midtbane": ["SUCCESSFULPASSES", "RECOVERIES", "DUELSWON", "KEYPASSES"],
        "Forsvarer": ["DUELSWON", "INTERCEPTIONS", "CLEARANCES", "AERIALDUELSWON"],
        "Målmand": ["GKSAVES", "GKSUCCESSFULEXITS"]
    }

    aktive_metrikker = metrik_mapping.get(valgt_gruppe, ["SUCCESSFULPASSES", "DUELSWON"])

    for idx, (komp_id, liga_navn) in enumerate(liga_mapping.items()):
        with kolonner[idx]:
            st.markdown(f"#### {liga_navn}")

            if not komp_col:
                st.error("Kunne ikke finde turnering-kolonne i data.")
                continue

            liga_df = df[(df[komp_col].astype(str).str.contains(str(komp_id))) & (df[pos_col] == valgt_gruppe)].copy()

            if liga_df.empty:
                st.info("Ingen spillere fundet.")
                continue

            # Konverter minutter og udregn P90 for de valgte rå kolonner
            mins_col = next((c for c in ['MINUTESONFIELD', 'MINUTES', 'MIN'] if c in liga_df.columns), None)
            
            Eksisterende_metrikker = []
            for m in aktive_metrikker:
                match_col = next((c for c in liga_df.columns if m.replace(" ", "") in c.replace(" ", "")), None)
                if match_col:
                    Eksisterende_metrikker.append(match_col)

            if not Eksisterende_metrikker:
                Eksisterende_metrikker = [c for c in liga_df.select_dtypes(include=['number']).columns if c not in [mins_col, 'SCORE']][:3]

            if not Eksisterende_metrikker:
                st.info("Ingen relevante metrics fundet.")
                continue

            liga_df['SCORE'] = 0
            for m in Eksisterende_metrikker:
                liga_df[m] = pd.to_numeric(liga_df[m], errors='coerce').fillna(0)
                if mins_col and mins_col in liga_df.columns:
                    mins = pd.to_numeric(liga_df[mins_col], errors='coerce').fillna(1)
                    p90_val = (liga_df[m] / mins) * 90
                else:
                    p90_val = liga_df[m]
                liga_df['SCORE'] += p90_val

            top10 = liga_df.sort_values(by='SCORE', ascending=False).head(10)

            navn_col = next((c for c in ['PLAYERNAME', 'NAVN', 'PLAYER_NAME', 'NAME'] if c in top10.columns), top10.columns[0])
            hold_col = next((c for c in ['TEAMNAME', 'KLUB', 'TEAM_NAME'] if c in top10.columns), None)

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
