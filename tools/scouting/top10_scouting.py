import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.sql.wy_queries import get_wy_queries
from utils.positional_helper import beregn_primaere_positioner, POSITIONSGRUPPE_ORDEN, METRICS_BY_GROUP

def vis_side(advanced_stats_df=None, position_base_df=None):
    st.markdown("### Top 10 Scouting – Divisioner", unsafe_allow_html=True)
    
    queries = get_wy_queries(comp_filter="(328, 329, 43319)", season_filter=None)
    
    conn = _get_snowflake_conn()
    if not conn:
        st.warning("Kunne ikke oprette forbindelse til databasen.")
        return

    try:
        df = conn.query(queries["players_top10"])
    except Exception as e:
        st.error(f"Fejl ved hentning af top10 data: {e}")
        return

    if df is None or df.empty:
        st.warning("Ingen data tilgængelig fra databasen.")
        return

    df.columns = [str(c).upper().strip() for c in df.columns]
    for col in ['PLAYER_WYID', 'COMPETITION_WYID']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str)

    if position_base_df is None or position_base_df.empty:
        try:
            unikt_id_liste = tuple(df['PLAYER_WYID'].dropna().unique())
            if unikt_id_liste:
                if len(unikt_id_liste) == 1:
                    id_str = f"('{unikt_id_liste[0]}')"
                else:
                    id_str = str(unikt_id_liste)
                
                pos_query_template = queries["position_base"]
                pos_query = pos_query_template.format(id_list=id_str)
                position_base_df = conn.query(pos_query)
        except Exception:
            pass

    df['POS_GROUP'] = 'Ukendt'

    if position_base_df is not None and not position_base_df.empty:
        pos_base = position_base_df.copy()
        pos_base.columns = [c.upper().strip() for c in pos_base.columns]
        
        if 'PLAYER_WYID' in pos_base.columns:
            pos_base['PLAYER_WYID'] = pd.to_numeric(pos_base['PLAYER_WYID'], errors='coerce').fillna(0).astype(int).astype(str)
            
            try:
                beregned_pos = beregn_primaere_positioner(pos_base)
                if beregned_pos is not None and not beregned_pos.empty:
                    beregned_pos.columns = [c.upper().strip() for c in beregned_pos.columns]
                    if 'PLAYER_WYID' in beregned_pos.columns and 'PRIMAER_POSITIONSGRUPPE' in beregned_pos.columns:
                        beregned_pos['PLAYER_WYID'] = pd.to_numeric(beregned_pos['PLAYER_WYID'], errors='coerce').fillna(0).astype(int).astype(str)
                        
                        df = df.merge(beregned_pos[['PLAYER_WYID', 'PRIMAER_POSITIONSGRUPPE']], on='PLAYER_WYID', how='left')
                        if 'PRIMAER_POSITIONSGRUPPE' in df.columns:
                            df['POS_GROUP'] = df['PRIMAER_POSITIONSGRUPPE'].fillna('Ukendt')
            except Exception as e:
                st.error(f"Fejl ved beregning af positioner: {e}")

    df['POS_GROUP'] = df['POS_GROUP'].fillna('Angriber')

    # Aggreger data pr. spiller og turnering for at undgå dubletter
    agg_cols_to_sum = [c for c in df.select_dtypes(include=['number']).columns if c not in ['COMPETITION_WYID', 'PLAYER_WYID', 'SEASON_WYID']]
    agg_regler = {col: 'sum' for col in agg_cols_to_sum}
    for col in ['PLAYER_NAME', 'TEAMNAME', 'POS_GROUP']:
        if col in df.columns:
            agg_regler[col] = 'first'
            
    df = df.groupby(['PLAYER_WYID', 'COMPETITION_WYID'], as_index=False).agg(agg_regler)

    # Brug POSITIONSGRUPPE_ORDEN direkte, så alle positioner altid kan vælges
    mulige_grupper = [g for g in POSITIONSGRUPPE_ORDEN if g != "Ukendt"]
    andre_grupper = sorted([g for g in df['POS_GROUP'].dropna().unique() if g not in POSITIONSGRUPPE_ORDEN and g != "Ukendt"])
    mulige_grupper = mulige_grupper + [g for g in andre_grupper if g not in mulige_grupper]

    if not mulige_grupper:
        mulige_grupper = ["Angriber", "Kant", "Central Midtbane", "Back", "Midtstopper", "Målmand"]

    valgt_gruppe = st.selectbox("Vælg Positionsgruppe", mulige_grupper)

    liga_mapping = {
        "328": "1. Division",
        "329": "2. Division",
        "43319": "3. Division"
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

            liga_df = df[(df[komp_col].astype(str) == str(komp_id)) & (df['POS_GROUP'] == valgt_gruppe)].copy()

            if liga_df.empty:
                st.info("Ingen spillere fundet.")
                continue

            mins_col = 'MINUTESONFIELD'
            liga_df['SCORE'] = 0
            antal_aktive_metrics = 0

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
                fallback_cols = [c for c in liga_df.select_dtypes(include=['number']).columns if c not in [mins_col, 'SCORE', komp_col]][:3]
                for m in fallback_cols:
                    liga_df[m] = pd.to_numeric(liga_df[m], errors='coerce').fillna(0)
                    liga_df['SCORE'] += liga_df[m]

            liga_df = liga_df.drop_duplicates(subset=['PLAYER_WYID'])
            top10 = liga_df.sort_values(by='SCORE', ascending=False).head(10)

            navn_col = 'PLAYER_NAME' if 'PLAYER_NAME' in top10.columns else 'SHORTNAME'
            hold_col = 'TEAMNAME' if 'TEAMNAME' in top10.columns else None

            for i, (_, row) in enumerate(top10.iterrows(), 1):
                p_navn = str(row.get(navn_col, "Spiller")) if navn_col else "Ukendt spiller"
                p_hold = str(row.get(hold_col, "")) if hold_col else ""
                p_score = round(float(row.get('SCORE', 0)), 2)
                
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
