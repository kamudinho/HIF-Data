import streamlit as st
import pandas as pd
from utils.positional_helper import POSITION_GROUP_MAP

def vis_side(advanced_stats_df, position_base_df=None):
    st.markdown("### Top 10 Scouting – Divisioner", unsafe_allow_html=True)
    
    if advanced_stats_df is None or advanced_stats_df.empty:
        st.warning("Ingen avanceret statistik tilgængelig.")
        return

    df = advanced_stats_df.copy()
    df.columns = [c.upper().strip() for c in df.columns]

    # Sikr POS_GROUP via roller/positioner eller fast fallback uden eksterne afhængigheder
    pos_col = 'POS_GROUP'
    if pos_col not in df.columns or df[pos_col].isna().all():
        role_col = next((c for c in ['ROLECODE3', 'ROLE_CODE3', 'ROLECODE', 'POSITION', 'POSITION1CODE'] if c in df.columns), None)
        if role_col:
            df['POS_GROUP'] = df[role_col].astype(str).str.lower().str.strip().map(POSITION_GROUP_MAP).fillna('Angriber')
        else:
            df['POS_GROUP'] = 'Angriber'

    mulige_grupper = sorted([g for g in df['POS_GROUP'].dropna().unique() if str(g).lower() != "ukendt"])
    if not mulige_grupper:
        mulige_grupper = ["Angriber", "Kant", "Central Midtbane", "Forsvarer", "Målmand"]

    valgt_gruppe = st.selectbox("Vælg Positionsgruppe", mulige_grupper)

    liga_mapping = {
        328: "1. Division",
        329: "2. Division",
        43319: "3. Division"
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
                st.error("Kunne ikke finde turneringskolonne i data.")
                continue

            liga_df = df[(df[komp_col].astype(str).str.contains(str(komp_id))) & (df['POS_GROUP'] == valgt_gruppe)].copy()

            if liga_df.empty:
                st.info("Ingen spillere fundet.")
                continue

            mins_col = next((c for c in ['MINUTESONFIELD', 'MINUTES', 'MIN'] if c in liga_df.columns), None)
            
            Eksisterende_metrikker = []
            for m in aktive_metrikker:
                match_col = next((c for c in liga_df.columns if m.replace(" ", "") in c.replace(" ", "")), None)
                if match_col:
                    Eksisterende_metrikker.append(match_col)

            if not Eksisterende_metrikker:
                Eksisterende_metrikker = [c for c in liga_df.select_dtypes(include=['number']).columns if c not in [mins_col, 'SCORE', 'PLAYER_WYID']][:3]

            if not Eksisterende_metrikker:
                st.info("Ingen relevante metrics fundet.")
                continue

            liga_df['SCORE'] = 0
            for m in Eksisterende_metrikker:
                liga_df[m] = pd.to_numeric(liga_df[m], errors='coerce').fillna(0)
                if mins_col and mins_col in liga_df.columns:
                    mins = pd.to_numeric(liga_df[mins_col], errors='coerce').fillna(1)
                    mins = mins.apply(lambda x: max(x, 1))
                    p90_val = (liga_df[m] / mins) * 90
                else:
                    p90_val = liga_df[m]
                liga_df['SCORE'] += p90_val

            top10 = liga_df.sort_values(by='SCORE', ascending=False).head(10)

            navn_col = next((c for c in ['PLAYER_NAME', 'PLAYERNAME', 'NAVN', 'NAME', 'SHORTNAME'] if c in top10.columns), None)
            hold_col = next((c for c in ['TEAMNAME', 'TEAM_NAME', 'KLUB'] if c in top10.columns), None)

            for i, (_, row) in enumerate(top10.iterrows(), 1):
                p_navn = row.get(navn_col, "Spiller") if navn_col else "Ukendt spiller"
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
