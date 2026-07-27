import streamlit as st
import pandas as pd
from decimal import Decimal

def vis_side():
    try:
        st.caption("Winning Performance")
        
        from data.data_load import _get_snowflake_conn
        conn = _get_snowflake_conn()
        
        if not conn:
            st.error("Kunne ikke oprette forbindelse til Snowflake.")
            return

        DB = "KLUB_HVIDOVREIF.AXIS"
        SEASONNAME = "2025/2026"
        TEAM_WYID = 7490
        
        sql = f"""
            WITH MatchBase AS (
                SELECT 
                    MATCH_OPTAUUID, MATCH_DATE_FULL, MATCH_STATUS,
                    CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                    TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE
                FROM {DB}.OPTA_MATCHINFO
            ),
            StatsPivot AS (
                SELECT 
                    MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                    MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN STAT_TOTAL END) AS POSSESSION,
                    SUM(CASE WHEN STAT_TYPE = 'totalPass' THEN STAT_TOTAL ELSE 0 END) AS PASSES,
                    SUM(CASE WHEN STAT_TYPE = 'accuratePass' THEN STAT_TOTAL ELSE 0 END) AS ACCURATE_PASSES,
                    SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS,
                    SUM(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS_ON_TARGET,
                    SUM(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN STAT_TOTAL ELSE 0 END) AS SHOT_OFF_TARGET,
                    SUM(CASE WHEN STAT_TYPE = 'blockedScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS BLOCKED_SHOTS,
                    SUM(CASE WHEN STAT_TYPE = 'wonTackle' THEN STAT_TOTAL ELSE 0 END) AS TACKLES_WON,
                    SUM(CASE WHEN STAT_TYPE = 'totalTackle' THEN STAT_TOTAL ELSE 0 END) AS TOTAL_TACKLES,
                    SUM(CASE WHEN STAT_TYPE = 'totalFoul' THEN STAT_TOTAL ELSE 0 END) AS FOULS,
                    SUM(CASE WHEN STAT_TYPE = 'cornerTaken' THEN STAT_TOTAL ELSE 0 END) AS CORNER_TAKEN,
                    SUM(CASE WHEN STAT_TYPE = 'wonCorners' THEN STAT_TOTAL ELSE 0 END) AS WON_CORNERS,
                    SUM(CASE WHEN STAT_TYPE = 'lostCorners' THEN STAT_TOTAL ELSE 0 END) AS LOST_CORNERS,
                    SUM(CASE WHEN STAT_TYPE = 'totalThrows' THEN STAT_TOTAL ELSE 0 END) AS TOTAL_THROWS,
                    SUM(CASE WHEN STAT_TYPE = 'goalKicks' THEN STAT_TOTAL ELSE 0 END) AS GOAL_KICKS,
                    SUM(CASE WHEN STAT_TYPE = 'totalClearance' THEN STAT_TOTAL ELSE 0 END) AS TOTAL_CLEARANCE,
                    SUM(CASE WHEN STAT_TYPE = 'totalOffside' THEN STAT_TOTAL ELSE 0 END) AS TOTAL_OFFSIDE,
                    SUM(CASE WHEN STAT_TYPE = 'saves' THEN STAT_TOTAL ELSE 0 END) AS SAVES,
                    SUM(CASE WHEN STAT_TYPE = 'subsMade' THEN STAT_TOTAL ELSE 0 END) AS SUBS_MADE,
                    SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) AS GOALS,
                    SUM(CASE WHEN STAT_TYPE = 'goalsConceded' THEN STAT_TOTAL ELSE 0 END) AS GOALS_CONCEDED,
                    SUM(CASE WHEN STAT_TYPE = 'goalAssist' THEN STAT_TOTAL ELSE 0 END) AS GOAL_ASSIST,
                    SUM(CASE WHEN STAT_TYPE = 'fkFoulWon' THEN STAT_TOTAL ELSE 0 END) AS FK_FOUL_WON,
                    SUM(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN STAT_TOTAL ELSE 0 END) AS FK_FOUL_LOST
                FROM {DB}.OPTA_MATCHSTATS
                GROUP BY 1, 2
            ),
            XGPivot AS (
                SELECT 
                    MATCH_ID, CONTESTANT_OPTAUUID,
                    SUM(CASE WHEN STAT_TYPE IN ('expectedGoals', 'expectedGoal') THEN STAT_VALUE ELSE 0 END) AS XG,
                    SUM(CASE WHEN STAT_TYPE = 'bigChanceCreated' THEN STAT_VALUE ELSE 0 END) AS BIG_CHANCES,
                    SUM(CASE WHEN STAT_TYPE = 'preventedGoals' THEN STAT_VALUE ELSE 0 END) AS PREVENTED_GOALS
                FROM {DB}.OPTA_MATCHEXPECTEDGOALS
                GROUP BY 1, 2
            ),
            BoxEntriesPivot AS (
                SELECT 
                    MATCH_OPTAUUID, 
                    EVENT_CONTESTANT_OPTAUUID AS CONTESTANT_OPTAUUID,
                    SUM(CASE 
                        WHEN EVENT_TYPEID IN (1, 13) 
                             AND EVENT_OUTCOME = 1 
                             AND EVENT_X >= 83 
                             AND EVENT_Y BETWEEN 21 AND 79 
                        THEN 1 ELSE 0 
                    END) AS CALCULATED_BOX_ENTRIES
                FROM {DB}.OPTA_EVENTS
                GROUP BY 1, 2
            ),
            FinalThirdPassesPivot AS (
                SELECT 
                    MATCH_OPTAUUID, 
                    EVENT_CONTESTANT_OPTAUUID AS CONTESTANT_OPTAUUID,
                    SUM(CASE 
                        WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 AND EVENT_X >= 66.6 
                        THEN 1 ELSE 0 
                    END) AS FT_PASSES_SUCCESSFUL,
                    SUM(CASE 
                        WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 0 AND EVENT_X >= 66.6 
                        THEN 1 ELSE 0 
                    END) AS FT_PASSES_UNSUCCESSFUL,
                    SUM(CASE 
                        WHEN EVENT_X >= 66.6 AND EVENT_TYPEID IN (13, 14, 15) 
                        THEN 1 ELSE 0 
                    END) AS FT_SHOTS_PRODUCED,
                    SUM(CASE 
                        WHEN EVENT_X >= 66.6 AND EVENT_TYPEID = 16 
                        THEN 1 ELSE 0 
                    END) AS FT_GOALS
                FROM {DB}.OPTA_EVENTS
                GROUP BY 1, 2
            ),
            AdvancedCalculations AS (
                SELECT 
                    MATCH_OPTAUUID,
                    EVENT_CONTESTANT_OPTAUUID AS CONTESTANT_OPTAUUID,
                    SUM(CASE WHEN EVENT_TYPEID = 4 THEN 1 ELSE 0 END) AS FOULS_COMMITTED,
                    SUM(CASE WHEN EVENT_TYPEID = 7 AND EVENT_X < 66.6 THEN 1 ELSE 0 END) AS TACKLES_DEF,
                    SUM(CASE WHEN EVENT_TYPEID = 8 AND EVENT_X < 66.6 THEN 1 ELSE 0 END) AS INTERCEPTIONS,
                    SUM(CASE WHEN EVENT_TYPEID = 1 AND EVENT_X < 66.6 THEN 1 ELSE 0 END) AS OPP_PASSES_ALLOWED
                FROM {DB}.OPTA_EVENTS
                GROUP BY 1, 2
            )
            SELECT 
                b.*,
                h.POSSESSION AS HOME_POSS, h.PASSES AS HOME_PASSES, h.ACCURATE_PASSES AS HOME_ACC_PASSES,
                h.SHOTS AS HOME_SHOTS, h.SHOTS_ON_TARGET AS HOME_SHOTS_ON_TARGET, h.SHOT_OFF_TARGET AS HOME_SHOT_OFF_TARGET,
                h.BLOCKED_SHOTS AS HOME_BLOCKED_SHOTS, h.TACKLES_WON AS HOME_TACKLES_WON, h.TOTAL_TACKLES AS HOME_TOTAL_TACKLES,
                h.FOULS AS HOME_FOULS,
                h.CORNER_TAKEN AS HOME_CORNER_TAKEN, h.WON_CORNERS AS HOME_WON_CORNERS, h.LOST_CORNERS AS HOME_LOST_CORNERS,
                h.TOTAL_THROWS AS HOME_TOTAL_THROWS, h.GOAL_KICKS AS HOME_GOAL_KICKS, h.TOTAL_CLEARANCE AS HOME_TOTAL_CLEARANCE,
                h.TOTAL_OFFSIDE AS HOME_TOTAL_OFFSIDE, h.SAVES AS HOME_SAVES, h.SUBS_MADE AS HOME_SUBS_MADE,
                h.GOALS AS HOME_GOALS, h.GOALS_CONCEDED AS HOME_GOALS_CONCEDED, h.GOAL_ASSIST AS HOME_GOAL_ASSIST,
                h.FK_FOUL_WON AS HOME_FK_FOUL_WON, h.FK_FOUL_LOST AS HOME_FK_FOUL_LOST,
                hx.XG AS HOME_XG, hx.BIG_CHANCES AS HOME_BIG_CHANCES, hx.PREVENTED_GOALS AS HOME_PREV_GOALS, 
                h_box.CALCULATED_BOX_ENTRIES AS HOME_BOX_ENTRIES,
                h_ft.FT_PASSES_SUCCESSFUL AS HOME_FT_SUCCESS, h_ft.FT_PASSES_UNSUCCESSFUL AS HOME_FT_UNSUCCESS,
                h_ft.FT_SHOTS_PRODUCED AS HOME_FT_SHOTS, h_ft.FT_GOALS AS HOME_FT_GOALS,
                h_adv.FOULS_COMMITTED AS HOME_FOULS_COMMITTED, h_adv.TACKLES_DEF AS HOME_TACKLES_DEF, h_adv.INTERCEPTIONS AS HOME_INTERCEPTIONS, h_adv.OPP_PASSES_ALLOWED AS HOME_OPP_PASSES_ALLOWED,
                
                a.POSSESSION AS AWAY_POSS, a.PASSES AS AWAY_PASSES, a.ACCURATE_PASSES AS AWAY_ACC_PASSES,
                a.SHOTS AS AWAY_SHOTS, a.SHOTS_ON_TARGET AS AWAY_SHOTS_ON_TARGET, a.SHOT_OFF_TARGET AS AWAY_SHOT_OFF_TARGET,
                a.BLOCKED_SHOTS AS AWAY_BLOCKED_SHOTS, a.TACKLES_WON AS AWAY_TACKLES_WON, a.TOTAL_TACKLES AS AWAY_TOTAL_TACKLES,
                a.FOULS AS AWAY_FOULS,
                a.CORNER_TAKEN AS AWAY_CORNER_TAKEN, a.WON_CORNERS AS AWAY_WON_CORNERS, a.LOST_CORNERS AS AWAY_LOST_CORNERS,
                a.TOTAL_THROWS AS AWAY_TOTAL_THROWS, a.GOAL_KICKS AS AWAY_GOAL_KICKS, a.TOTAL_CLEARANCE AS AWAY_TOTAL_CLEARANCE,
                a.TOTAL_OFFSIDE AS AWAY_TOTAL_OFFSIDE, a.SAVES AS AWAY_SAVES, a.SUBS_MADE AS AWAY_SUBS_MADE,
                a.GOALS AS AWAY_GOALS, a.GOALS_CONCEDED AS AWAY_GOALS_CONCEDED, a.GOAL_ASSIST AS AWAY_GOAL_ASSIST,
                a.FK_FOUL_WON AS AWAY_FK_FOUL_WON, a.FK_FOUL_LOST AS AWAY_FK_FOUL_LOST,
                ax.XG AS AWAY_XG, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, ax.PREVENTED_GOALS AS AWAY_PREV_GOALS, 
                a_box.CALCULATED_BOX_ENTRIES AS AWAY_BOX_ENTRIES,
                a_ft.FT_PASSES_SUCCESSFUL AS AWAY_FT_SUCCESS, a_ft.FT_PASSES_UNSUCCESSFUL AS AWAY_FT_UNSUCCESS,
                a_ft.FT_SHOTS_PRODUCED AS AWAY_FT_SHOTS, a_ft.FT_GOALS AS AWAY_FT_GOALS,
                a_adv.FOULS_COMMITTED AS AWAY_FOULS_COMMITTED, a_adv.TACKLES_DEF AS AWAY_TACKLES_DEF, a_adv.INTERCEPTIONS AS AWAY_INTERCEPTIONS, a_adv.OPP_PASSES_ALLOWED AS AWAY_OPP_PASSES_ALLOWED
            FROM MatchBase b
            LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
            LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
            LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
            LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
            LEFT JOIN BoxEntriesPivot h_box ON b.MATCH_OPTAUUID = h_box.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h_box.CONTESTANT_OPTAUUID
            LEFT JOIN BoxEntriesPivot a_box ON b.MATCH_OPTAUUID = a_box.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a_box.CONTESTANT_OPTAUUID
            LEFT JOIN FinalThirdPassesPivot h_ft ON b.MATCH_OPTAUUID = h_ft.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h_ft.CONTESTANT_OPTAUUID
            LEFT JOIN FinalThirdPassesPivot a_ft ON b.MATCH_OPTAUUID = a_ft.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a_ft.CONTESTANT_OPTAUUID
            LEFT JOIN AdvancedCalculations h_adv ON b.MATCH_OPTAUUID = h_adv.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h_adv.CONTESTANT_OPTAUUID
            LEFT JOIN AdvancedCalculations a_adv ON b.MATCH_OPTAUUID = a_adv.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a_adv.CONTESTANT_OPTAUUID
        """

        with st.spinner("Henter data..."):
            df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

        if df_matches is None or df_matches.empty:
            st.warning("SQL-forespørgslen returnerede ingen rækker.")
            return

        df_matches.columns = [str(c).upper() for c in df_matches.columns]
        played = df_matches[df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()

        match_rows = []
        for _, row in played.iterrows():
            h_uuid = str(row['CONTESTANTHOME_OPTAUUID']).strip().upper()
            a_uuid = str(row['CONTESTANTAWAY_OPTAUUID']).strip().upper()
            
            h_score = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
            a_score = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
            
            h_passes = float(row.get('HOME_PASSES', 0) or 0)
            h_acc = float(row.get('HOME_ACC_PASSES', 0) or 0)
            h_pass_pct = (h_acc / h_passes * 100.0) if h_passes > 0 else 0.0
            
            h_def_actions = float(row.get('HOME_TACKLES_DEF', 0) or 0) + float(row.get('HOME_INTERCEPTIONS', 0) or 0) + float(row.get('HOME_FOULS_COMMITTED', 0) or 0)
            a_opp_passes = float(row.get('AWAY_OPP_PASSES_ALLOWED', 0) or 0)
            h_ppda = (a_opp_passes / h_def_actions) if h_def_actions > 0 else 0.0

            a_passes = float(row.get('AWAY_PASSES', 0) or 0)
            a_acc = float(row.get('AWAY_ACC_PASSES', 0) or 0)
            a_pass_pct = (a_acc / a_passes * 100.0) if a_passes > 0 else 0.0
            
            a_def_actions = float(row.get('AWAY_TACKLES_DEF', 0) or 0) + float(row.get('AWAY_INTERCEPTIONS', 0) or 0) + float(row.get('AWAY_FOULS_COMMITTED', 0) or 0)
            h_opp_passes = float(row.get('HOME_OPP_PASSES_ALLOWED', 0) or 0)
            a_ppda = (h_opp_passes / a_def_actions) if a_def_actions > 0 else 0.0

            h_poss_pct = float(pd.to_numeric(row.get('HOME_POSS'), errors='coerce') or 50.0)
            a_poss_pct = float(pd.to_numeric(row.get('AWAY_POSS'), errors='coerce') or 50.0)

            h_total_sec = (h_poss_pct / 100.0) * 5400.0
            h_seq_count = max(1.0, h_passes * 0.4)
            h_sec_per_seq = h_total_sec / h_seq_count

            a_total_sec = (a_poss_pct / 100.0) * 5400.0
            a_seq_count = max(1.0, a_passes * 0.4)
            a_sec_per_seq = a_total_sec / a_seq_count

            h_res = 'Sejr' if h_score > a_score else ('Uafgjort' if h_score == a_score else 'Nederlag')
            h_dict = {
                'TEAM_UUID': h_uuid,
                'RESULTAT': h_res,
                'POSS': h_poss_pct,
                'PASSES': h_passes,
                'PASS_PCT': h_pass_pct,
                'SHOTS': pd.to_numeric(row.get('HOME_SHOTS'), errors='coerce'),
                'SHOTS_ON_TARGET': pd.to_numeric(row.get('HOME_SHOTS_ON_TARGET'), errors='coerce'),
                'SHOT_OFF_TARGET': pd.to_numeric(row.get('HOME_SHOT_OFF_TARGET'), errors='coerce'),
                'BLOCKED_SHOTS': pd.to_numeric(row.get('HOME_BLOCKED_SHOTS'), errors='coerce'),
                'TACKLES': pd.to_numeric(row.get('HOME_TACKLES_WON'), errors='coerce'),
                'TOTAL_TACKLES': pd.to_numeric(row.get('HOME_TOTAL_TACKLES'), errors='coerce'),
                'FOULS': pd.to_numeric(row.get('HOME_FOULS'), errors='coerce'),
                'CORNER_TAKEN': pd.to_numeric(row.get('HOME_CORNER_TAKEN'), errors='coerce'),
                'WON_CORNERS': pd.to_numeric(row.get('HOME_WON_CORNERS'), errors='coerce'),
                'LOST_CORNERS': pd.to_numeric(row.get('HOME_LOST_CORNERS'), errors='coerce'),
                'TOTAL_THROWS': pd.to_numeric(row.get('HOME_TOTAL_THROWS'), errors='coerce'),
                'GOAL_KICKS': pd.to_numeric(row.get('HOME_GOAL_KICKS'), errors='coerce'),
                'TOTAL_CLEARANCE': pd.to_numeric(row.get('HOME_TOTAL_CLEARANCE'), errors='coerce'),
                'TOTAL_OFFSIDE': pd.to_numeric(row.get('HOME_TOTAL_OFFSIDE'), errors='coerce'),
                'SAVES': pd.to_numeric(row.get('HOME_SAVES'), errors='coerce'),
                'SUBS_MADE': pd.to_numeric(row.get('HOME_SUBS_MADE'), errors='coerce'),
                'GOALS_CONCEDED': pd.to_numeric(row.get('HOME_GOALS_CONCEDED'), errors='coerce'),
                'FK_FOUL_WON': pd.to_numeric(row.get('HOME_FK_FOUL_WON'), errors='coerce'),
                'FK_FOUL_LOST': pd.to_numeric(row.get('HOME_FK_FOUL_LOST'), errors='coerce'),
                'XG': pd.to_numeric(row.get('HOME_XG'), errors='coerce'),
                'BIG_CHANCES': pd.to_numeric(row.get('HOME_BIG_CHANCES'), errors='coerce'),
                'PREv_GOALS': pd.to_numeric(row.get('HOME_PREV_GOALS'), errors='coerce'),
                'BOX_ENTRIES': pd.to_numeric(row.get('HOME_BOX_ENTRIES'), errors='coerce'),
                'FT_SUCCESS': pd.to_numeric(row.get('HOME_FT_SUCCESS'), errors='coerce'),
                'FT_UNSUCCESS': pd.to_numeric(row.get('HOME_FT_UNSUCCESS'), errors='coerce'),
                'FT_SHOTS': pd.to_numeric(row.get('HOME_FT_SHOTS'), errors='coerce'),
                'FT_GOALS': pd.to_numeric(row.get('HOME_FT_GOALS'), errors='coerce'),
                'PPDA': h_ppda,
                'BALL_TIME_SEQ': h_sec_per_seq
            }
            match_rows.append(h_dict)

            a_res = 'Sejr' if a_score > h_score else ('Uafgjort' if a_score == h_score else 'Nederlag')
            a_dict = {
                'TEAM_UUID': a_uuid,
                'RESULTAT': a_res,
                'POSS': a_poss_pct,
                'PASSES': a_passes,
                'PASS_PCT': a_pass_pct,
                'SHOTS': pd.to_numeric(row.get('AWAY_SHOTS'), errors='coerce'),
                'SHOTS_ON_TARGET': pd.to_numeric(row.get('AWAY_SHOTS_ON_TARGET'), errors='coerce'),
                'SHOT_OFF_TARGET': pd.to_numeric(row.get('AWAY_SHOT_OFF_TARGET'), errors='coerce'),
                'BLOCKED_SHOTS': pd.to_numeric(row.get('AWAY_BLOCKED_SHOTS'), errors='coerce'),
                'TACKLES': pd.to_numeric(row.get('AWAY_TACKLES_WON'), errors='coerce'),
                'TOTAL_TACKLES': pd.to_numeric(row.get('AWAY_TOTAL_TACKLES'), errors='coerce'),
                'FOULS': pd.to_numeric(row.get('AWAY_FOULS'), errors='coerce'),
                'CORNER_TAKEN': pd.to_numeric(row.get('AWAY_CORNER_TAKEN'), errors='coerce'),
                'WON_CORNERS': pd.to_numeric(row.get('AWAY_WON_CORNERS'), errors='coerce'),
                'LOST_CORNERS': pd.to_numeric(row.get('AWAY_LOST_CORNERS'), errors='coerce'),
                'TOTAL_THROWS': pd.to_numeric(row.get('AWAY_TOTAL_THROWS'), errors='coerce'),
                'GOAL_KICKS': pd.to_numeric(row.get('AWAY_GOAL_KICKS'), errors='coerce'),
                'TOTAL_CLEARANCE': pd.to_numeric(row.get('AWAY_TOTAL_CLEARANCE'), errors='coerce'),
                'TOTAL_OFFSIDE': pd.to_numeric(row.get('AWAY_TOTAL_OFFSIDE'), errors='coerce'),
                'SAVES': pd.to_numeric(row.get('AWAY_SAVES'), errors='coerce'),
                'SUBS_MADE': pd.to_numeric(row.get('AWAY_SUBS_MADE'), errors='coerce'),
                'GOALS_CONCEDED': pd.to_numeric(row.get('AWAY_GOALS_CONCEDED'), errors='coerce'),
                'FK_FOUL_WON': pd.to_numeric(row.get('AWAY_FK_FOUL_WON'), errors='coerce'),
                'FK_FOUL_LOST': pd.to_numeric(row.get('AWAY_FK_FOUL_LOST'), errors='coerce'),
                'XG': pd.to_numeric(row.get('AWAY_XG'), errors='coerce'),
                'BIG_CHANCES': pd.to_numeric(row.get('AWAY_BIG_CHANCES'), errors='coerce'),
                'PREv_GOALS': pd.to_numeric(row.get('AWAY_PREV_GOALS'), errors='coerce'),
                'BOX_ENTRIES': pd.to_numeric(row.get('AWAY_BOX_ENTRIES'), errors='coerce'),
                'FT_SUCCESS': pd.to_numeric(row.get('AWAY_FT_SUCCESS'), errors='coerce'),
                'FT_UNSUCCESS': pd.to_numeric(row.get('AWAY_FT_UNSUCCESS'), errors='coerce'),
                'FT_SHOTS': pd.to_numeric(row.get('AWAY_FT_SHOTS'), errors='coerce'),
                'FT_GOALS': pd.to_numeric(row.get('AWAY_FT_GOALS'), errors='coerce'),
                'PPDA': a_ppda,
                'BALL_TIME_SEQ': a_sec_per_seq
            }
            match_rows.append(a_dict)

        df_perf = pd.DataFrame(match_rows)
        team_perf = df_perf.dropna(subset=['TEAM_UUID'])

        if not team_perf.empty:
            cols_to_mean = [
                'POSS', 'PASSES', 'PASS_PCT', 'SHOTS', 'SHOTS_ON_TARGET', 'SHOT_OFF_TARGET', 'BLOCKED_SHOTS',
                'TACKLES', 'TOTAL_TACKLES', 'FOULS', 'CORNER_TAKEN', 'WON_CORNERS',
                'LOST_CORNERS', 'TOTAL_THROWS', 'GOAL_KICKS', 'TOTAL_CLEARANCE', 'TOTAL_OFFSIDE', 'SAVES',
                'SUBS_MADE', 'GOALS_CONCEDED', 'FK_FOUL_WON', 'FK_FOUL_LOST', 'XG', 'BIG_CHANCES', 'PREv_GOALS', 
                'BOX_ENTRIES', 'FT_SUCCESS', 'FT_UNSUCCESS', 'FT_SHOTS', 'FT_GOALS', 'PPDA', 'BALL_TIME_SEQ'
            ]
            summary_table = team_perf.groupby('RESULTAT')[cols_to_mean].mean().reindex(['Sejr', 'Uafgjort', 'Nederlag']).T
            
            summary_table.index = [
                'Boldbesiddelse (%)', 
                'Afleveringer (Total)', 
                'Pasningsprocent (%)', 
                'Afslutninger (Total)', 
                'Afslutninger (Inden for ramme)', 
                'Afslutninger (Uden for ramme)',
                'Blokerede afslutninger',
                'Vundne Tacklinger', 
                'Tacklinger (Total)',
                'Frispark begået', 
                'Hjørnespark',
                'Vundne hjørnespark',
                'Tabte hjørnespark',
                'Indkast',
                'Målspark',
                'Clearinger',
                'Offsides',
                'Redninger',
                'Foretagne udskiftninger',
                'Mål indkasseret',
                'Frispark vundet',
                'Frispark tabt',
                'xG (Forventede Mål)', 
                'Store Chancer', 
                'Prevented Goals',
                'Box Entries',
                'Final Third: Succesfulde Afleveringer',
                'Final Third: Afleveringer',
                'Final Third: Afslutninger',
                'Final Third: Mål',
                'PPDA (Passes Per Defensive Action)',
                'Boldbesiddelsestid pr. sekvens (sek)'
            ]

            def color_goals(row):
                styles = [''] * len(row)
                row_name = str(row.name)
                
                for i, col_name in enumerate(row.index):
                    if col_name == 'Sejr':
                        val = row[col_name]
                        try:
                            v = float(val)
                        except:
                            continue
                            
                        if "Pasningsprocent" in row_name and v >= 78:
                            styles[i] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
                        elif "Box Entries" in row_name and v >= 10:
                            styles[i] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
                        elif "xG" in row_name and v >= 1.2:
                            styles[i] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
                        elif "PPDA" in row_name and v <= 13:
                            styles[i] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
                return styles

            def get_val(metric_name):
                try:
                    return f"{summary_table.loc[metric_name, 'Sejr']:.1f}"
                except:
                    return "N/A"

            tab1, tab2 = st.tabs(["Datagrundlag", "Winning Performance Model"])

            with tab1:
                st.markdown("Alle gennemsnitlige præstationsmål fordelt på kampens udfald")
                
                styled_summary = summary_table.style.format("{:.2f}").apply(color_goals, axis=1)
                
                st.dataframe(
                    styled_summary,
                    use_container_width=True
                )
                st.info(f"Tabellen viser alle metrikker opdelt efter Sejr, Uafgjort og Nederlag for sæson {SEASONNAME}.")

            with tab2:
                st.markdown("Winning Performance Model (Fase-opdelt målstruktur med faktiske snit ved Sejre)")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown('##### <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="20" style="vertical-align: middle; margin-right: 8px;"> OPBYGNINGSSPIL', unsafe_allow_html=True)
                    st.markdown(f"- **Pasningsprocent:** {get_val('Pasningsprocent (%)')} (Mål: >78%)")
                    st.markdown(f"- **Afleveringer (Total):** {get_val('Afleveringer (Total)')}")
                    st.markdown(f"- **Boldbesiddelse:** {get_val('Boldbesiddelse (%)')}%")
                    st.markdown(f"- **Afslutninger (Total):** {get_val('Afslutninger (Total)')}")

                with col2:
                    st.markdown('##### <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="20" style="vertical-align: middle; margin-right: 8px;"> AFSLUTNINGSSPIL', unsafe_allow_html=True)
                    st.markdown(f"- **xG (Forventede Mål):** {get_val('xG (Forventede Mål)')}")
                    st.markdown(f"- **Store Chancer:** {get_val('Store Chancer')}")
                    st.markdown(f"- **Box Entries:** {get_val('Box Entries')} (Mål: >10)")
                    st.markdown(f"- **FT Succesfulde Afleveringer:** {get_val('Final Third: Succesfulde Afleveringer')}")
                    st.markdown(f"- **Afslutninger på mål:** {get_val('Afslutninger (Inden for ramme)')}")

                with col3:
                    st.markdown('##### <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="20" style="vertical-align: middle; margin-right: 8px;"> FORSVARSSPIL', unsafe_allow_html=True)
                    st.markdown(f"- **Mål indkasseret:** {get_val('Mål indkasseret')}")
                    st.markdown(f"- **Vundne Tacklinger:** {get_val('Vundne Tacklinger')}")

                with col4:
                    st.markdown('##### <img src="https://cdn5.wyscout.com/photos/team/public/2659_120x120.png" width="20" style="vertical-align: middle; margin-right: 8px;"> EROBRINGSSPIL', unsafe_allow_html=True)
                    st.markdown(f"- **PPDA:** {get_val('PPDA (Passes Per Defensive Action)')} (Mål: <13)")
                    st.markdown(f"- **Boldbesiddelsestid pr. sekvens:** {get_val('Boldbesiddelsestid pr. sekvens (sek)')} sek")
                    st.markdown(f"- **Hjørnespark:** {get_val('Hjørnespark')}")

        else:
            st.warning("Ikke nok data tilgængelig.")

    except Exception as e:
        st.error(f"Der opstod en fejl på siden: {e}")
