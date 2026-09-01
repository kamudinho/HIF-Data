import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from utils.positional_helper import METRICS_BY_GROUP

@st.cache_data(ttl=600)
def hent_scouting_data():
    conn = _get_snowflake_conn()
    if not conn:
        return None

    query = """
    WITH ranked_base AS (
        SELECT 
            PLAYER_WYID,
            SEASON_WYID,
            COMPETITION_WYID,
            CASE 
                WHEN GREATEST(COALESCE(POSITIONS1PERCENT,0), COALESCE(POSITIONS2PERCENT,0), COALESCE(POSITIONS3PERCENT,0), COALESCE(POSITIONS4PERCENT,0)) <= 0 THEN NULL
                WHEN COALESCE(POSITIONS1PERCENT, 0) >= GREATEST(COALESCE(POSITIONS2PERCENT,0), COALESCE(POSITIONS3PERCENT,0), COALESCE(POSITIONS4PERCENT,0)) THEN POSITION1CODE
                WHEN COALESCE(POSITIONS2PERCENT, 0) >= GREATEST(COALESCE(POSITIONS1PERCENT,0), COALESCE(POSITIONS3PERCENT,0), COALESCE(POSITIONS4PERCENT,0)) THEN POSITION2CODE
                WHEN COALESCE(POSITIONS3PERCENT, 0) >= GREATEST(COALESCE(POSITIONS1PERCENT,0), COALESCE(POSITIONS2PERCENT,0), COALESCE(POSITIONS4PERCENT,0)) THEN POSITION3CODE
                ELSE POSITION4CODE
            END AS PRIMARY_POS_CODE
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERADVANCEDSTATS_BASE
    ),
    ranked_players AS (
        SELECT
            pt.PLAYER_WYID,
            p.SHORTNAME AS PLAYER_NAME,
            t.TEAMNAME,
            pt.COMPETITION_WYID,
            s.SEASONNAME,
            
            -- Specifik undergruppe (finere opdeling til filtrering)
            CASE 
                WHEN rb.PRIMARY_POS_CODE IS NULL THEN 'Ukendt'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) = 'GK' THEN 'Målmand'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('RCB', 'RCB3') THEN 'Højre Stopper'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('LCB', 'LCB3') THEN 'Venstre Stopper'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('CB', 'CB3') THEN 'Central Stopper'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('RB', 'RWB', 'RB3', 'RB5') THEN 'Højre Back'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('LB', 'LWB', 'LB3', 'LB5') THEN 'Venstre Back'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('DMF', 'LDMF', 'RDMF') THEN 'Defensiv Midtbane (6''er)'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('CMF', 'LCMF', 'RCMF', 'LCMF3', 'RCMF3') THEN 'Central Midtbane (8''er)'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('AMF', 'LAMF', 'RAMF') THEN 'Offensiv Midtbane (10''er)'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('RW', 'RWF') THEN 'Højre Kant'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('LW', 'LWF') THEN 'Venstre Kant'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('CF', 'ST', 'SS') THEN 'Angriber'
                ELSE CONCAT('Ukendt Code: ', rb.PRIMARY_POS_CODE)
            END AS POS_SPECIFIC,

            -- Overordnet hovedgruppe (til valg i første dropdown)
            CASE 
                WHEN rb.PRIMARY_POS_CODE IS NULL THEN 'Ukendt'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) = 'GK' THEN 'Målmand'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('CB', 'LCB', 'RCB', 'LCB3', 'RCB3', 'CB3') THEN 'Stopper'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('RB', 'LB', 'RWB', 'LWB', 'RB3', 'LB3', 'RB5', 'LB5') THEN 'Back'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('DMF', 'LDMF', 'RDMF', 'CMF', 'LCMF', 'RCMF', 'LCMF3', 'RCMF3', 'AMF', 'LAMF', 'RAMF') THEN 'Midtbane'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('LW', 'RW', 'LWF', 'RWF') THEN 'Kant'
                WHEN UPPER(TRIM(rb.PRIMARY_POS_CODE)) IN ('CF', 'ST', 'SS') THEN 'Angriber'
                ELSE 'Ukendt'
            END AS POS_GROUP,

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
            pt.GKAERIALDUELSWON,
            ROW_NUMBER() OVER (
                PARTITION BY pt.PLAYER_WYID, pt.COMPETITION_WYID 
                ORDER BY pt.MINUTESONFIELD DESC
            ) as rn
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERADVANCEDSTATS_TOTAL pt
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_SEASONS s ON pt.SEASON_WYID = s.SEASON_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS p ON pt.PLAYER_WYID = p.PLAYER_WYID AND pt.SEASON_WYID = p.SEASON_WYID AND pt.COMPETITION_WYID = p.COMPETITION_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
        LEFT JOIN ranked_base rb 
            ON pt.PLAYER_WYID = rb.PLAYER_WYID 
            AND pt.SEASON_WYID = rb.SEASON_WYID
            AND pt.COMPETITION_WYID = rb.COMPETITION_WYID
        WHERE pt.COMPETITION_WYID IN (328, 329, 43319)
          AND s.ACTIVE = TRUE
    )
    SELECT * FROM ranked_players WHERE rn = 1;
    """
    try:
        return conn.query(query)
    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
        return None

def vis_side(advanced_stats_df=None, position_base_df=None):
    
    df = hent_scouting_data()
    if df is None or df.empty:
        st.warning("Ingen data tilgængelig fra databasen.")
        return

    df.columns = [str(c).upper().strip() for c in df.columns]
    for col in ['PLAYER_WYID', 'COMPETITION_WYID']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str)

    hoved_grupper = ["Målmand", "Stopper", "Back", "Midtbane", "Kant", "Angriber"]
    
    col_left1, col_left2, col_right = st.columns([1.2, 1.2, 1.8])

    with col_left1:
        st.markdown("**Positionsgruppe**")
        valgt_hovedgruppe = st.selectbox("Hovedgruppe", hoved_grupper, label_visibility="collapsed")

    mapping_under = {
        "Målmand": ["Målmand"],
        "Stopper": ["Alle Stoppere", "Højre Stopper", "Venstre Stopper", "Central Stopper"],
        "Back": ["Alle Backs", "Højre Back", "Venstre Back"],
        "Midtbane": ["Alle Midtbaner", "Defensiv Midtbane (6'er)", "Central Midtbane (8'er)", "Offensiv Midtbane (10'er)"],
        "Kant": ["Alle Kanter", "Højre Kant", "Venstre Kant"],
        "Angriber": ["Angriber"]
    }

    tilgængelige_under = mapping_under.get(valgt_hovedgruppe, [valgt_hovedgruppe])

    with col_left2:
        st.markdown("**Pladsspecifik**")
        valgt_gruppe = st.selectbox("Specifik", tilgængelige_under, label_visibility="collapsed")

    gruppe_definitioner = METRICS_BY_GROUP.get(valgt_gruppe, METRICS_BY_GROUP.get(valgt_hovedgruppe, METRICS_BY_GROUP["Ukendt"]))
    
    beskrivelse_dele = []
    for m_def in gruppe_definitioner:
        b_type = m_def[0]
        if b_type == "p90":
            _, navn, kolonne = m_def
            beskrivelse_dele.append(f"**{navn}** (pr. 90 min)")
        elif b_type == "pct":
            _, navn, succes_kol, total_kol = m_def
            beskrivelse_dele.append(f"**{navn}** (% succes)")

    metrics_tekst = ", ".join(beskrivelse_dele) if beskrivelse_dele else "Ingen specifikke nøgletal defineret."

    with col_right:
        st.markdown(f"""
            <div style='height: 100%; min-height: 72px; padding: 10px 14px; background: #f8f9fa; border-left: 4px solid #df003b; border-radius: 4px; font-size: 0.85rem; color: #333; display: flex; align-items: center;'>
                <div><b>Beregning for {valgt_gruppe}:</b> {metrics_tekst}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

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

    for idx, (komp_id, liga_navn) in enumerate(liga_mapping.items()):
        with kolonner[idx]:
            st.markdown(f"#### {liga_navn}")

            if valgt_gruppe.startswith("Alle "):
                søg_term = valgt_hovedgruppe
                liga_df = df[(df[komp_col].astype(str) == str(komp_id)) & (df['POS_SPECIFIC'].str.contains(søg_term, case=False, na=False))].copy()
            else:
                liga_df = df[(df[komp_col].astype(str) == str(komp_id)) & (df['POS_SPECIFIC'] == valgt_gruppe)].copy()

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

            for i, (_, row) in enumerate(top10.iterrows(), 1):
                p_navn = str(row.get('PLAYER_NAME', "Ukendt spiller"))
                p_hold = str(row.get('TEAMNAME', ""))
                p_score = round(float(row.get('SCORE', 0)), 2)
                
                st.markdown(f"""
                    <div style='padding: 5px 8px; margin-bottom: 4px; background: #fff; border: 1px solid #eee; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;'>
                        <div style='line-height: 1.2;'>
                            <span style='font-weight: bold; color: #df003b; margin-right: 4px;'>{i}.</span> 
                            <span style='font-weight: 600; font-size: 0.85rem;'>{p_navn}</span>
                            <span style='font-size: 0.7rem; color: gray; margin-left: 4px;'>({p_hold})</span>
                        </div>
                        <div style='text-align: right;'>
                            <span style='font-weight: 800; font-size: 0.85rem;'>{p_score}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
