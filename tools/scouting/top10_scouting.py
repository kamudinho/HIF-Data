import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from utils.positional_helper import beregn_primaere_positioner, POSITIONSGRUPPE_ORDEN, METRICS_BY_GROUP

@st.cache_data(ttl=600)
def _hent_top10_data():
    conn = _get_snowflake_conn()
    if not conn:
        return pd.DataFrame()
    
    DB = "KLUB_HVIDOVREIF.AXIS"
    query = f"""
        SELECT DISTINCT
            pt.PLAYER_WYID,
            p.SHORTNAME AS PLAYER_NAME,
            t.TEAMNAME,
            pt.COMPETITION_WYID,
            s.SEASONNAME,
            pt.MINUTESONFIELD,
            pt.GOALS,
            pt.ASSISTS,
            pt.SHOTS,
            pt.XGSHOT,
            pt.XGASSIST,
            pt.DRIBBLES,
            pt.SUCCESSFULDRIBBLES,
            pt.PROGRESSIVERUN,
            pt.PROGRESSIVEPASSES,
            pt.SUCCESSFULPROGRESSIVEPASSES,
            pt.PASSES,
            pt.SUCCESSFULPASSES,
            pt.KEYPASSES,
            pt.RECOVERIES,
            pt.INTERCEPTIONS,
            pt.DUELS,
            pt.DUELSWON,
            pt.DEFENSIVEDUELS,
            pt.DEFENSIVEDUELSWON,
            pt.AERIALDUELS,
            pt.AERIALDUELSWON,
            pt.CLEARANCES,
            pt.SLIDINGTACKLES,
            pt.SUCCESSFULSLIDINGTACKLES,
            pt.CROSSES,
            pt.SUCCESSFULCROSSES,
            pt.TOUCHINBOX,
            pt.GKSAVES,
            pt.GKCONCEDEDGOALS,
            pt.GKEXITS,
            pt.GKSUCCESSFULEXITS,
            pt.GKAERIALDUELS,
            pt.GKAERIALDUELSWON
        FROM {DB}.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL pt
        JOIN {DB}.WYSCOUT_SEASONS s ON pt.SEASON_WYID = s.SEASON_WYID
        JOIN {DB}.WYSCOUT_PLAYERS p ON pt.PLAYER_WYID = p.PLAYER_WYID AND pt.SEASON_WYID = p.SEASON_WYID
        JOIN {DB}.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
        WHERE pt.COMPETITION_WYID IN (329, 43319, 328)
          AND s.ACTIVE = TRUE
    """
    try:
        df = conn.query(query)
        if df is not None and not df.empty:
            df.columns = [str(c).upper().strip() for c in df.columns]
            for col in ['PLAYER_WYID', 'COMPETITION_WYID']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str)
        return df
    except Exception as e:
        st.error(f"Fejl ved direkte hentning af top10 data: {e}")
        return pd.DataFrame()

def vis_side(advanced_stats_df=None, position_base_df=None):
    st.write("DEBUG - Kolonner i dataframe:", list(df.columns))
    st.write(df.head(2))
    
    st.markdown("### Top 10 Scouting – Divisioner", unsafe_allow_html=True)

    df = _hent_top10_data()
    
    if df is None or df.empty:
        st.warning("Ingen data tilgængelig fra databasen.")
        return

    if position_base_df is None or position_base_df.empty:
        try:
            conn = _get_snowflake_conn()
            if conn:
                pos_query = f"SELECT PLAYER_WYID, POSITION, POSITIONSGROUP FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS"
                position_base_df = conn.query(pos_query)
        except:
            pass

    if position_base_df is not None and not position_base_df.empty:
        pos_base = position_base_df.copy()
        pos_base.columns = [c.upper().strip() for c in pos_base.columns]
        
        if 'PLAYER_WYID' in df.columns and 'PLAYER_WYID' in pos_base.columns:
            df['TEMP_ID'] = df['PLAYER_WYID']
            pos_base['TEMP_ID'] = pd.to_numeric(pos_base['PLAYER_WYID'], errors='coerce').fillna(0).astype(int).astype(str)
            
            try:
                beregned_pos = beregn_primaere_positioner(pos_base)
                if beregned_pos is not None and not beregned_pos.empty:
                    beregned_pos.columns = [c.upper().strip() for c in beregned_pos.columns]
                    if 'PLAYER_WYID' in beregned_pos.columns and 'PRIMAER_POSITIONSGRUPPE' in beregned_pos.columns:
                        beregned_pos['TEMP_ID'] = pd.to_numeric(beregned_pos['PLAYER_WYID'], errors='coerce').fillna(0).astype(int).astype(str)
                        df = df.merge(beregned_pos[['TEMP_ID', 'PRIMAER_POSITIONSGRUPPE']], on='TEMP_ID', how='left')
                        df = df.rename(columns={'PRIMAER_POSITIONSGRUPPE': 'POS_GROUP'})
            except Exception as e:
                st.error(f"Fejl ved beregning af positioner: {e}")

    if 'POS_GROUP' not in df.columns or df['POS_GROUP'].isna().all():
        df['POS_GROUP'] = 'Ukendt'

    tilgængelige_grupper = [g for g in POSITIONSGRUPPE_ORDEN if g in df['POS_GROUP'].unique() and g != "Ukendt"]
    andre_grupper = sorted([g for g in df['POS_GROUP'].dropna().unique() if g not in POSITIONSGRUPPE_ORDEN and g != "Ukendt"])
    mulige_grupper = tilgængelige_grupper + andre_grupper

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
                fallback_cols = [c for c in liga_df.select_dtypes(include=['number']).columns if c not in [mins_col, 'SCORE', 'TEMP_ID', komp_col]][:3]
                for m in fallback_cols:
                    liga_df[m] = pd.to_numeric(liga_df[m], errors='coerce').fillna(0)
                    liga_df['SCORE'] += liga_df[m]

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
