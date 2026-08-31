import streamlit as st
import pandas as pd
from utils.positional_helper import beregn_primaere_positioner, POSITIONSGRUPPE_ORDEN, METRICS_BY_GROUP

def vis_side(advanced_stats_df, position_base_df=None):
    st.markdown("### Top 10 Scouting – Divisioner", unsafe_allow_html=True)
    
    if advanced_stats_df is None or advanced_stats_df.empty:
        st.warning("Ingen avanceret statistik tilgængelig.")
        return

    df = advanced_stats_df.copy()
    df.columns = [c.upper().strip() for c in df.columns]

    # 1. Beregn positioner via positional_helper og position_base_df
    if position_base_df is not None and not position_base_df.empty:
        pos_base = position_base_df.copy()
        pos_base.columns = [c.upper().strip() for c in pos_base.columns]
        
        id_adv = 'PLAYER_WYID' if 'PLAYER_WYID' in df.columns else None
        id_pos = 'PLAYER_WYID' if 'PLAYER_WYID' in pos_base.columns else None
        
        if id_adv and id_pos:
            df['TEMP_ID'] = df[id_adv].astype(str).str.split('.').str[0].str.strip()
            pos_base['TEMP_ID'] = pos_base[id_pos].astype(str).str.split('.').str[0].str.strip()
            
            try:
                beregned_pos = beregn_primaere_positioner(pos_base)
                if beregned_pos is not None and not beregned_pos.empty:
                    beregned_pos.columns = [c.upper().strip() for c in beregned_pos.columns]
                    if 'PLAYER_WYID' in beregned_pos.columns and 'PRIMAER_POSITIONSGRUPPE' in beregned_pos.columns:
                        beregned_pos['TEMP_ID'] = beregned_pos['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
                        df = df.merge(beregned_pos[['TEMP_ID', 'PRIMAER_POSITIONSGRUPPE']], on='TEMP_ID', how='left')
                        df = df.rename(columns={'PRIMAER_POSITIONSGRUPPE': 'POS_GROUP'})
            except Exception as e:
                st.error(f"Fejl ved beregning af positioner: {e}")

    if 'POS_GROUP' not in df.columns or df['POS_GROUP'].isna().all():
        df['POS_GROUP'] = 'Ukendt'

    # Sorter positionsgrupperne pænt
    tilgængelige_grupper = [g for g in POSITIONSGRUPPE_ORDEN if g in df['POS_GROUP'].unique() and g != "Ukendt"]
    andre_grupper = sorted([g for g in df['POS_GROUP'].dropna().unique() if g not in POSITIONSGRUPPE_ORDEN and g != "Ukendt"])
    mulige_grupper = tilgængelige_grupper + andre_grupper

    if not mulige_grupper:
        mulige_grupper = ["Angriber", "Kant", "Central Midtbane", "Back", "Midtstopper", "Målmand"]

    valgt_gruppe = st.selectbox("Vælg Positionsgruppe", mulige_grupper)

    # 2. Match præcist med de turnerings-ID'er din SQL henter ind (328, 329, 43319)
    liga_mapping = {
        328: "1. Division",
        329: "2. Division",
        43319: "3. Division"
    }

    komp_col = 'COMPETITION_WYID'
    if komp_col not in df.columns:
        st.error(f"Kolonnen '{komp_col}' blev ikke fundet i data.")
        return
    
    col1, col2, col3 = st.columns(3)
    kolonner = [col1, col2, col3]

    gruppe_definitioner = METRICS_BY_GROUP.get(valgt_gruppe, METRICS_BY_GROUP["Ukendt"])

    for idx, (komp_id, liga_navn) in enumerate(liga_mapping.items()):
        with kolonner[idx]:
            st.markdown(f"#### {liga_navn}")

            # Filtrer direkte på det specifikke turnerings-ID fra din SQL
            liga_df = df[(df[komp_col].astype(str) == str(komp_id)) & (df['POS_GROUP'] == valgt_gruppe)].copy()

            if liga_df.empty:
                st.info("Ingen spillere fundet.")
                continue

            mins_col = 'MINUTESONFIELD'
            liga_df['SCORE'] = 0
            antal_aktive_metrics = 0

            # Beregn score ud fra de definerede metrics i positional_helper
            for metrik_def in gruppe_definitioner:
                beregn_type = metrik_def[0]
                
                if beregn_type == "p90":
                    _, _, kolonne = metrik_def
                    if kolonne in liga_df.columns:
                        liga_df[kolonne] = pd.to_numeric(liga_df[kolonne], errors='coerce').fillna(0)
                        if mins_col in liga_df.columns:
                            mins = pd.to_numeric(liga_df[mins_col], errors='coerce').fillna(1).apply(lambda x: max(x, 1))
                            p90_val = (liga_df[kolonne] / mins) * 90
                        else:
                            p90_val = liga_df[kolonne]
                        liga_df['SCORE'] += p90_val
                        antal_aktive_metrics += 1
                        
                elif beregn_type == "pct":
                    _, _, succes_kol, total_kol = metrik_def
                    if succes_kol in liga_df.columns and total_kol in liga_df.columns:
                        liga_df[succes_kol] = pd.to_numeric(liga_df[succes_kol], errors='coerce').fillna(0)
                        liga_df[total_kol] = pd.to_numeric(liga_df[total_kol], errors='coerce').fillna(0)
                        pct_val = (liga_df[succes_kol] / liga_df[total_kol].replace(0, 1)) * 100
                        liga_df['SCORE'] += pct_val
                        antal_aktive_metrics += 1

            if antal_aktive_metrics == 0:
                fallback_cols = [c for c in liga_df.select_dtypes(include=['number']).columns if c not in [mins_col, 'SCORE', 'TEMP_ID', komp_col]][:3]
                for m in fallback_cols:
                    liga_df[m] = pd.to_numeric(liga_df[m], errors='coerce').fillna(0)
                    liga_df['SCORE'] += liga_df[m]

            top10 = liga_df.sort_values(by='SCORE', ascending=False).head(10)

            navn_col = 'PLAYER_NAME' if 'PLAYER_NAME' in top10.columns else 'SHORTNAME'
            hold_col = 'TEAMNAME' if 'TEAMNAME' in top10.columns else None

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
