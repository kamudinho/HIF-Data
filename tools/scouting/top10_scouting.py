import streamlit as st
import pandas as pd
from utils.positional_helper import beregn_primaere_positioner, POSITION_GROUP_MAP

def vis_side(advanced_stats_df, position_base_df=None):
    st.markdown("### Top 10 Scouting – Divisioner", unsafe_allow_html=True)
    
    if advanced_stats_df is None or advanced_stats_df.empty:
        st.warning("Ingen avanceret statistik tilgængelig.")
        return

    df = advanced_stats_df.copy()
    df.columns = [c.upper().strip() for c in df.columns]

    # Hvis position_base_df ikke blev sendt med som argument, prøv at hente den via hif_load
    scouting_pkg = {}
    if position_base_df is None or position_base_df.empty:
        try:
            import data.hif_load as hif_load
            scouting_pkg = hif_load.get_scouting_package()
            if scouting_pkg and "primaer_positioner" in scouting_pkg:
                position_base_df = scouting_pkg["primaer_positioner"]
        except Exception:
            pass

    # Sørg for at få positionsgruppe med på df
    pos_col = 'POS_GROUP'
    if pos_col not in df.columns:
        if position_base_df is not None and not position_base_df.empty:
            pos_base_temp = position_base_df.copy()
            pos_base_temp.columns = [c.upper().strip() for c in pos_base_temp.columns]
            
            id_col_adv = next((c for c in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID'] if c in df.columns), None)
            id_col_pos = next((c for c in ['PLAYER_WYID', 'WYID', 'PLAYER_ID', 'ID'] if c in pos_base_temp.columns), None)
            
            if id_col_adv and id_col_pos:
                df['TEMP_ID'] = df[id_col_adv].astype(str).str.split('.').str[0].str.strip()
                pos_base_temp['TEMP_ID'] = pos_base_temp[id_col_pos].astype(str).str.split('.').str[0].str.strip()
                
                # Find kolonne til gruppe
                pos_col_name = next((c for c in ['PRIMAER_POSITIONSGRUPPE', 'POSITIONSGRUPPE', 'GROUP', 'POS_GROUP'] if c in pos_base_temp.columns), None)
                if pos_col_name:
                    df = df.merge(pos_base_temp[['TEMP_ID', pos_col_name]], on='TEMP_ID', how='left')
                    df = df.rename(columns={pos_col_name: 'POS_GROUP'})

        # Fallback hvis POS_GROUP stadig mangler
        if 'POS_GROUP' not in df.columns or df['POS_GROUP'].isna().all():
            role_col = next((c for c in ['ROLECODE3', 'ROLE_CODE3', 'ROLECODE', 'POSITION', 'POSITION1CODE'] if c in df.columns), None)
            if role_col:
                df['POS_GROUP'] = df[role_col].astype(str).str.lower().str.strip().map(POSITION_GROUP_MAP).fillna('Ukendt')
            else:
                df['POS_GROUP'] = 'Ukendt'

    # Hvis 'PLAYER_NAME' eller 'TEAMNAME' mangler i advanced_stats_df, berig via wyscout_players fra pakken
    if not any(c in df.columns for c in ['PLAYER_NAME', 'PLAYERNAME', 'NAVN']):
        if not scouting_pkg:
            try:
                import data.hif_load as hif_load
                scouting_pkg = hif_load.get_scouting_package()
            except:
                pass
        
        wyscout_pl = scouting_pkg.get("wyscout_players") if scouting_pkg else None
        if wyscout_pl is not None and not wyscout_pl.empty:
            w_temp = wyscout_pl.copy()
            w_temp.columns = [c.upper().strip() for c in w_temp.columns]
            id_adv = next((c for c in ['PLAYER_WYID', 'WYID'] if c in df.columns), None)
            id_w = next((c for c in ['PLAYER_WYID', 'WYID'] if c in w_temp.columns), None)
            
            if id_adv and id_w:
                df['TEMP_ID'] = df[id_adv].astype(str).str.split('.').str[0].str.strip()
                w_temp['TEMP_ID'] = w_temp[id_w].astype(str).str.split('.').str[0].str.strip()
                
                # Vælg relevante kolonner hvis de findes
                merge_cols = ['TEMP_ID']
                for col_kand in ['PLAYER_NAME', 'PLAYERNAME', 'NAME', 'TEAMNAME', 'TEAM_NAME', 'KLUB']:
                    if col_kand in w_temp.columns and col_kand not in merge_cols:
                        merge_cols.append(col_kand)
                
                if len(merge_cols) > 1:
                    df = df.merge(w_temp[merge_cols], on='TEMP_ID', how='left', suffixes=('', '_wy'))

    mulige_grupper = sorted([g for g in df['POS_GROUP'].dropna().unique() if str(g).lower() != "ukendt"])
    if not mulige_grupper:
        mulige_grupper = ["Angriber", "Kant", "Central Midtbane", "Forsvarer", "Målmand"]

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
                Eksisterende_metrikker = [c for c in liga_df.select_dtypes(include=['number']).columns if c not in [mins_col, 'SCORE', 'TEMP_ID']][:3]

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

            navn_col = next((c for c in ['PLAYER_NAME', 'PLAYERNAME', 'NAVN', 'NAME'] if c in top10.columns), None)
            hold_col = next((c for c in ['TEAMNAME', 'TEAM_NAME', 'KLUB'] if c in top10.columns), None)

            for i, (_, row) in enumerate(top10.iterrows(), 1):
                p_navn = row.get(navn_col, f"Spiller") if navn_col else "Ukendt spiller"
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
