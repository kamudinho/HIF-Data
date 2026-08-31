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

    # Brug positional_helper og position_base_df til at beregne og tildele primære positioner/grupper
    if position_base_df is not None and not position_base_df.empty:
        pos_base = position_base_df.copy()
        pos_base.columns = [c.upper().strip() for c in pos_base.columns]
        
        id_adv = next((c for c in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID'] if c in df.columns), None)
        id_pos = next((c for c in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID'] if c in pos_base.columns), None)
        
        if id_adv and id_pos:
            df['TEMP_ID'] = df[id_adv].astype(str).str.split('.').str[0].str.strip()
            pos_base['TEMP_ID'] = pos_base[id_pos].astype(str).str.split('.').str[0].str.strip()
            
            # Beregn eller flet positioner via hjælperen hvis den stilles til rådighed
            try:
                beregned_pos = beregn_primaere_positioner(pos_base)
                if beregned_pos is not None and not beregned_pos.empty:
                    beregned_pos.columns = [c.upper().strip() for c in beregned_pos.columns]
                    b_id = next((c for c in ['PLAYER_WYID', 'WYID', 'TEMP_ID'] if c in beregned_pos.columns), None)
                    b_grp = next((c for c in ['PRIMAER_POSITIONSGRUPPE', 'POSITIONSGRUPPE', 'POS_GROUP', 'GROUP'] if c in beregned_pos.columns), None)
                    if b_id and b_grp:
                        beregned_pos['TEMP_ID'] = beregned_pos[b_id].astype(str).str.split('.').str[0].str.strip()
                        df = df.merge(beregned_pos[['TEMP_ID', b_grp]], on='TEMP_ID', how='left')
                        df = df.rename(columns={b_grp: 'POS_GROUP'})
            except Exception:
                pass

            if 'POS_GROUP' not in df.columns or df['POS_GROUP'].isna().all():
                grp_col = next((c for c in ['PRIMAER_POSITIONSGRUPPE', 'POSITIONSGRUPPE', 'POS_GROUP', 'GROUP'] if c in pos_base.columns), None)
                if grp_col:
                    df = df.merge(pos_base[['TEMP_ID', grp_col]], on='TEMP_ID', how='left')
                    df = df.rename(columns={grp_col: 'POS_GROUP'})

    if 'POS_GROUP' not in df.columns or df['POS_GROUP'].isna().all():
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
                liga_df = df[df['POS_GROUP'] == valgt_gruppe].copy()
            else:
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
                Eksisterende_metrikker = [c for c in liga_df.select_dtypes(include=['number']).columns if c not in [mins_col, 'SCORE', 'TEMP_ID', 'PLAYER_WYID']][:3]

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
