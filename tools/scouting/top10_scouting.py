import streamlit as st
import pandas as pd
from data.data_load import _get_snowflake_conn
from utils.positional_helper import POSITIONSGRUPPE_ORDEN, METRICS_BY_GROUP

def vis_side(advanced_stats_df=None, position_base_df=None):
    st.markdown("### Top 10 Scouting – Divisioner", unsafe_allow_html=True)
    
    conn = _get_snowflake_conn()
    if not conn:
        st.warning("Kunne ikke oprette forbindelse til databasen.")
        return

    query = """
    WITH ranked_players AS (
        SELECT 
            pt.PLAYER_WYID,
            p.SHORTNAME AS PLAYER_NAME,
            t.TEAMNAME,
            pt.COMPETITION_WYID,
            s.SEASONNAME,
            
            CASE 
                WHEN GREATEST(
                    COALESCE(pb.POSITIONS1PERCENT, 0),
                    COALESCE(pb.POSITIONS2PERCENT, 0),
                    COALESCE(pb.POSITIONS3PERCENT, 0),
                    COALESCE(pb.POSITIONS4PERCENT, 0)
                ) = 0 THEN 'Ukendt'
                
                WHEN (
                    CASE 
                        WHEN pb.POSITIONS1PERCENT >= GREATEST(COALESCE(pb.POSITIONS2PERCENT,0), COALESCE(pb.POSITIONS3PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION1CODE
                        WHEN pb.POSITIONS2PERCENT >= GREATEST(COALESCE(pb.POSITIONS1PERCENT,0), COALESCE(pb.POSITIONS3PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION2CODE
                        WHEN pb.POSITIONS3PERCENT >= GREATEST(COALESCE(pb.POSITIONS1PERCENT,0), COALESCE(pb.POSITIONS2PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION3CODE
                        ELSE pb.POSITION4CODE
                    END
                ) IN ('GK') THEN 'Målmand'
                
                WHEN (
                    CASE 
                        WHEN pb.POSITIONS1PERCENT >= GREATEST(COALESCE(pb.POSITIONS2PERCENT,0), COALESCE(pb.POSITIONS3PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION1CODE
                        WHEN pb.POSITIONS2PERCENT >= GREATEST(COALESCE(pb.POSITIONS1PERCENT,0), COALESCE(pb.POSITIONS3PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION2CODE
                        WHEN pb.POSITIONS3PERCENT >= GREATEST(COALESCE(pb.POSITIONS1PERCENT,0), COALESCE(pb.POSITIONS2PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION3CODE
                        ELSE pb.POSITION4CODE
                    END
                ) IN ('CB', 'LCB', 'RCB') THEN 'Midtstopper'
                
                WHEN (
                    CASE 
                        WHEN pb.POSITIONS1PERCENT >= GREATEST(COALESCE(pb.POSITIONS2PERCENT,0), COALESCE(pb.POSITIONS3PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION1CODE
                        WHEN pb.POSITIONS2PERCENT >= GREATEST(COALESCE(pb.POSITIONS1PERCENT,0), COALESCE(pb.POSITIONS3PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION2CODE
                        WHEN pb.POSITIONS3PERCENT >= GREATEST(COALESCE(pb.POSITIONS1PERCENT,0), COALESCE(pb.POSITIONS2PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION3CODE
                        ELSE pb.POSITION4CODE
                    END
                ) IN ('LB', 'RB', 'LWB', 'RWB') THEN 'Back'
                
                WHEN (
                    CASE 
                        WHEN pb.POSITIONS1PERCENT >= GREATEST(COALESCE(pb.POSITIONS2PERCENT,0), COALESCE(pb.POSITIONS3PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION1CODE
                        WHEN pb.POSITIONS2PERCENT >= GREATEST(COALESCE(pb.POSITIONS1PERCENT,0), COALESCE(pb.POSITIONS3PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION2CODE
                        WHEN pb.POSITIONS3PERCENT >= GREATEST(COALESCE(pb.POSITIONS1PERCENT,0), COALESCE(pb.POSITIONS2PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION3CODE
                        ELSE pb.POSITION4CODE
                    END
                ) IN ('DMF', 'LCMF', 'RCMF', 'AMF', 'CMF') THEN 'Central Midtbane'
                
                WHEN (
                    CASE 
                        WHEN pb.POSITIONS1PERCENT >= GREATEST(COALESCE(pb.POSITIONS2PERCENT,0), COALESCE(pb.POSITIONS3PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION1CODE
                        WHEN pb.POSITIONS2PERCENT >= GREATEST(COALESCE(pb.POSITIONS1PERCENT,0), COALESCE(pb.POSITIONS3PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION2CODE
                        WHEN pb.POSITIONS3PERCENT >= GREATEST(COALESCE(pb.POSITIONS1PERCENT,0), COALESCE(pb.POSITIONS2PERCENT,0), COALESCE(pb.POSITIONS4PERCENT,0)) THEN pb.POSITION3CODE
                        ELSE pb.POSITION4CODE
                    END
                ) IN ('LW', 'RW', 'LWF', 'RWF') THEN 'Kant'
                
                ELSE 'Angriber'
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
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERS p ON pt.PLAYER_WYID = p.PLAYER_WYID AND pt.SEASON_WYID = p.SEASON_WYID
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS t ON p.CURRENTTEAM_WYID = t.TEAM_WYID
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_PLAYERADVANCEDSTATS_BASE pb ON pt.PLAYER_WYID = pb.PLAYER_WYID AND pt.SEASON_WYID = pb.SEASON_WYID
        WHERE pt.COMPETITION_WYID IN (328, 329, 43319)
          AND s.ACTIVE = TRUE
    )
    SELECT * FROM ranked_players WHERE rn = 1;
    """

    try:
        df = conn.query(query)
    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
        return

    if df is None or df.empty:
        st.warning("Ingen data tilgængelig fra databasen.")
        return

    df.columns = [str(c).upper().strip() for c in df.columns]
    for col in ['PLAYER_WYID', 'COMPETITION_WYID']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).astype(str)

    mulige_grupper = [g for g in POSITIONSGRUPPE_ORDEN if g != "Ukendt"]
    andre_grupper = sorted([g for g in df['POS_GROUP'].dropna().unique() if g not in POSITIONSGRUPPE_ORDEN and g != "Ukendt"])
    for g in andre_grupper:
        if g not in mulige_grupper:
            mulige_grupper.append(g)

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

            for i, (_, row) in enumerate(top10.iterrows(), 1):
                p_navn = str(row.get('PLAYER_NAME', "Ukendir spiller"))
                p_hold = str(row.get('TEAMNAME', ""))
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
