#data/sql/kampe.py
import os
import numpy as np
import pandas as pd
from data.data_load import _get_snowflake_conn
from data.sql.fallback import fill_gaps_team_row, FALLBACK_FILE
import streamlit as st

@st.cache_data(ttl=3600)
def load_match_level_data(
    tournament_opta_uuid,
    team_opta_uuid,
    team_wyid,
    comp_wyid,
    season_start_year=2026,
):
    # Opret forbindelse til databasen
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"

    # SQL-spørringen
    query = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, 
                TO_CHAR(MATCH_DATE_FULL, 'YYYY-MM-DD') AS MATCH_DATE,
                CONTESTANTHOME_OPTAUUID, 
                CONTESTANTAWAY_OPTAUUID,
                TOTAL_HOME_SCORE, 
                TOTAL_AWAY_SCORE
            FROM {db}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_opta_uuid}'
              AND MATCH_STATUS = 'Played'
              AND CAST(MATCH_DATE_FULL AS DATE) <= CURRENT_DATE()
              AND (CONTESTANTHOME_OPTAUUID = '{team_opta_uuid}' OR CONTESTANTAWAY_OPTAUUID = '{team_opta_uuid}')
        ),
        PlayerSubs AS (
            SELECT MATCH_OPTAUUID, PLAYER_OPTAUUID, MIN(EVENT_TIMESTAMP) AS SUB_TIME
            FROM {db}.OPTA_EVENTS
            WHERE EVENT_TYPEID = 19
            GROUP BY MATCH_OPTAUUID, PLAYER_OPTAUUID
        ),
        CalculatedSubGoals AS (
            SELECT 
                e.MATCH_OPTAUUID,
                e.EVENT_CONTESTANT_OPTAUUID AS CONTESTANT_OPTAUUID,
                COUNT(DISTINCT e.EVENT_OPTAUUID) AS SUBSGOALS
            FROM {db}.OPTA_EVENTS e
            JOIN PlayerSubs s ON e.MATCH_OPTAUUID = s.MATCH_OPTAUUID AND e.PLAYER_OPTAUUID = s.PLAYER_OPTAUUID
            LEFT JOIN {db}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 28
            WHERE e.EVENT_TYPEID = 16
              AND e.EVENT_TIMESTAMP > s.SUB_TIME
              AND q.EVENT_OPTAUUID IS NULL
            GROUP BY e.MATCH_OPTAUUID, e.EVENT_CONTESTANT_OPTAUUID
        ),
        MatchStatsPivot AS (
            -- RETTET: possessionPercentage er tidligere blevet parset med almindelig CAST
            -- uden at fjerne '%'. Værdien gemmes som streng med procenttegn (fx "45.0%"),
            -- og et almindeligt CAST af den streng FEJLER i Snowflake - det fik hele
            -- forespørgslen til at kaste en exception, som blev fanget nedenfor og fik
            -- siden til altid at falde tilbage til den statiske CSV-fil i stedet for at
            -- vise friske Snowflake-data. Samme mønster (TRY_CAST + REPLACE) som teams.py
            -- og konklusion_query.py bruges nu her. Alle øvrige felter er også lagt om til
            -- TRY_CAST i stedet for CAST, så én uventet værdi i ét felt ikke længere kan
            -- vælte hele forespørgslen og udløse alt-eller-intet-fallback.
            SELECT 
                MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                MAX(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS TOTALSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS ONTARGETSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'shotOffTarget' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS SHOTOFFTARGET,
                MAX(CASE WHEN STAT_TYPE = 'blockedScoringAtt' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS BLOCKEDSCORINGATT,
                MAX(CASE WHEN STAT_TYPE = 'totalPass' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS TOTALPASS,
                MAX(CASE WHEN STAT_TYPE = 'accuratePass' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS ACCURATEPASS,
                MAX(CASE WHEN STAT_TYPE = 'possessionPercentage' THEN TRY_CAST(REPLACE(STAT_TOTAL, '%', '') AS FLOAT) END) AS POSSESSIONPERCENTAGE,
                MAX(CASE WHEN STAT_TYPE = 'wonCorners' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS WONCORNERS,
                MAX(CASE WHEN STAT_TYPE = 'lostCorners' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS LOSTCORNERS,
                MAX(CASE WHEN STAT_TYPE = 'totalTackle' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS TOTALTACKLE,
                MAX(CASE WHEN STAT_TYPE = 'wonTackle' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS WONTACKLE,
                MAX(CASE WHEN STAT_TYPE = 'totalClearance' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS TOTALCLEARANCE,
                MAX(CASE WHEN STAT_TYPE = 'outfielderBlock' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS OUTFIELDERBLOCK,
                MAX(CASE WHEN STAT_TYPE = 'fkFoulWon' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS FKFOULWON,
                MAX(CASE WHEN STAT_TYPE = 'fkFoulLost' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS FKFOULLOST,
                MAX(CASE WHEN STAT_TYPE = 'saves' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS SAVES,
                MAX(CASE WHEN STAT_TYPE = 'goalsConceded' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS GOALSCONCEDED,
                MAX(CASE WHEN STAT_TYPE = 'cleanSheet' THEN TRY_CAST(STAT_TOTAL AS FLOAT) END) AS CLEANSHEET
            FROM {db}.OPTA_MATCHSTATS
            WHERE MATCH_OPTAUUID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
              AND CONTESTANT_OPTAUUID = '{team_opta_uuid}'
            GROUP BY 1, 2
        ),
        ExpectedGoalsPivot AS (
            SELECT 
                MATCH_ID AS MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                SUM(CASE WHEN STAT_TYPE = 'expectedGoals' THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS EXPECTEDGOALS,
                SUM(CASE WHEN STAT_TYPE = 'touchesInOppBox' THEN TRY_CAST(STAT_VALUE AS FLOAT) ELSE 0 END) AS TOUCHESINOPPBOX
            FROM {db}.OPTA_MATCHEXPECTEDGOALS
            WHERE MATCH_ID IN (SELECT MATCH_OPTAUUID FROM MatchBase)
            GROUP BY 1, 2
        ),
        WyscoutDefense AS (
            SELECT 
                TO_CHAR(tm.DATE, 'YYYY-MM-DD') AS MATCH_DATE,
                md.PPDA
            FROM {db}.WYSCOUT_TEAMMATCHES tm
            LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md 
                ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID
            WHERE tm.COMPETITION_WYID = {comp_wyid} AND tm.TEAM_WYID = {team_wyid}
        ),
        FullTournamentData AS (
            SELECT 
                mb.MATCH_OPTAUUID,
                mb.MATCH_DATE,
                '{team_opta_uuid}' AS TEAM_OPTAUUID,
                COALESCE(CASE WHEN '{team_opta_uuid}' = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_HOME_SCORE ELSE mb.TOTAL_AWAY_SCORE END, 0) AS GOALS,
                COALESCE(CASE WHEN '{team_opta_uuid}' = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_AWAY_SCORE ELSE mb.TOTAL_HOME_SCORE END, 0) AS GOALS_AGAINST,
                mb.CONTESTANTHOME_OPTAUUID,
                mb.CONTESTANTAWAY_OPTAUUID,
                -- NB: disse felter COALESCE'es bevidst IKKE til 0 her længere (kun GOALS/
                -- GOALS_AGAINST/SUBSGOALS ovenfor/nedenfor, hvor NULL fra en LEFT JOIN reelt
                -- betyder "0 forekomster af den event-type", ikke "data mangler"). Ægte
                -- manglende Opta-statistik skal stå som NULL herfra, så Python-fallbacken
                -- (fill_gaps_team_row, se data/sql/fallback.py) kan udfylde PRÆCIS de huller
                -- fra kampe_fallback.csv - samme "udfyld kun huller"-logik som teams.py bruger,
                -- i stedet for at hele kampens resultat erstattes med CSV'en.
                sp.TOTALSCORINGATT,
                sp.ONTARGETSCORINGATT,
                sp.SHOTOFFTARGET,
                sp.BLOCKEDSCORINGATT,
                COALESCE(csg.SUBSGOALS, 0) AS SUBSGOALS,
                sp.TOTALPASS,
                sp.ACCURATEPASS,
                sp.POSSESSIONPERCENTAGE,
                sp.WONCORNERS,
                sp.LOSTCORNERS,
                sp.TOTALTACKLE,
                sp.WONTACKLE,
                sp.TOTALCLEARANCE,
                sp.OUTFIELDERBLOCK,
                sp.FKFOULWON,
                sp.FKFOULLOST,
                sp.SAVES,
                sp.GOALSCONCEDED,
                sp.CLEANSHEET,
                xg.EXPECTEDGOALS,
                xg.TOUCHESINOPPBOX,
                opp_xg.TOUCHESINOPPBOX AS OPPONENT_TOUCHESINOPPBOX,
                wd.PPDA,
                (COALESCE(xg.EXPECTEDGOALS, 0) * 2.0 + COALESCE(CASE WHEN '{team_opta_uuid}' = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_HOME_SCORE ELSE mb.TOTAL_AWAY_SCORE END, 0) * 3.0 + COALESCE(sp.ONTARGETSCORINGATT, 0) * 1.0 + COALESCE(sp.TOTALSCORINGATT, 0) * 0.2 + COALESCE(xg.TOUCHESINOPPBOX, 0) * 0.1) AS OFFENSIV_INDEX,
                (COALESCE(sp.WONTACKLE, 0) * 1.0 + COALESCE(sp.TOTALCLEARANCE, 0) * 0.5 + COALESCE(sp.OUTFIELDERBLOCK, 0) * 1.0 + COALESCE(sp.CLEANSHEET, 0) * 3.0 - COALESCE(CASE WHEN '{team_opta_uuid}' = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_AWAY_SCORE ELSE mb.TOTAL_HOME_SCORE END, 0) * 2.0 - COALESCE(opp_xg.TOUCHESINOPPBOX, 0) * 0.1) AS DEFENSIV_INDEX,
                AVG(xg.EXPECTEDGOALS) OVER() AS LIGA_AVG_EXPECTEDGOALS,
                AVG(xg.TOUCHESINOPPBOX) OVER() AS LIGA_AVG_TOUCHESINOPPBOX,
                AVG(opp_xg.TOUCHESINOPPBOX) OVER() AS LIGA_AVG_OPPONENT_TOUCHESINOPPBOX,
                AVG(CASE WHEN '{team_opta_uuid}' = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_HOME_SCORE ELSE mb.TOTAL_AWAY_SCORE END) OVER() AS LIGA_AVG_GOALS,
                AVG(CASE WHEN '{team_opta_uuid}' = mb.CONTESTANTHOME_OPTAUUID THEN mb.TOTAL_AWAY_SCORE ELSE mb.TOTAL_HOME_SCORE END) OVER() AS LIGA_AVG_GOALS_AGAINST,
                AVG(sp.TOTALSCORINGATT) OVER() AS LIGA_AVG_TOTALSCORINGATT,
                AVG(sp.ONTARGETSCORINGATT) OVER() AS LIGA_AVG_ONTARGETSCORINGATT,
                AVG(sp.SHOTOFFTARGET) OVER() AS LIGA_AVG_SHOTOFFTARGET,
                AVG(sp.BLOCKEDSCORINGATT) OVER() AS LIGA_AVG_BLOCKEDSCORINGATT,
                AVG(csg.SUBSGOALS) OVER() AS LIGA_AVG_SUBSGOALS,
                AVG(sp.TOTALPASS) OVER() AS LIGA_AVG_TOTALPASS,
                AVG(sp.ACCURATEPASS) OVER() AS LIGA_AVG_ACCURATEPASS,
                AVG(sp.POSSESSIONPERCENTAGE) OVER() AS LIGA_AVG_POSSESSIONPERCENTAGE,
                AVG(sp.WONCORNERS) OVER() AS LIGA_AVG_WONCORNERS,
                AVG(sp.LOSTCORNERS) OVER() AS LIGA_AVG_LOSTCORNERS,
                AVG(sp.TOTALTACKLE) OVER() AS LIGA_AVG_TOTALTACKLE,
                AVG(sp.WONTACKLE) OVER() AS LIGA_AVG_WONTACKLE,
                AVG(sp.TOTALCLEARANCE) OVER() AS LIGA_AVG_TOTALCLEARANCE,
                AVG(sp.OUTFIELDERBLOCK) OVER() AS LIGA_AVG_OUTFIELDERBLOCK,
                AVG(sp.FKFOULWON) OVER() AS LIGA_AVG_FKFOULWON,
                AVG(sp.FKFOULLOST) OVER() AS LIGA_AVG_FKFOULLOST,
                AVG(sp.SAVES) OVER() AS LIGA_AVG_SAVES,
                AVG(sp.GOALSCONCEDED) OVER() AS LIGA_AVG_GOALSCONCEDED,
                AVG(sp.CLEANSHEET) OVER() AS LIGA_AVG_CLEANSHEET,
                AVG(wd.PPDA) OVER() AS LIGA_AVG_PPDA
            FROM MatchBase mb
            LEFT JOIN MatchStatsPivot sp ON mb.MATCH_OPTAUUID = sp.MATCH_OPTAUUID
            LEFT JOIN CalculatedSubGoals csg ON mb.MATCH_OPTAUUID = csg.MATCH_OPTAUUID AND csg.CONTESTANT_OPTAUUID = '{team_opta_uuid}'
            LEFT JOIN ExpectedGoalsPivot xg ON mb.MATCH_OPTAUUID = xg.MATCH_OPTAUUID AND xg.CONTESTANT_OPTAUUID = '{team_opta_uuid}'
            LEFT JOIN ExpectedGoalsPivot opp_xg ON mb.MATCH_OPTAUUID = opp_xg.MATCH_OPTAUUID AND opp_xg.CONTESTANT_OPTAUUID = CASE WHEN mb.CONTESTANTHOME_OPTAUUID = '{team_opta_uuid}' THEN mb.CONTESTANTAWAY_OPTAUUID ELSE mb.CONTESTANTHOME_OPTAUUID END
            LEFT JOIN WyscoutDefense wd ON mb.MATCH_DATE = wd.MATCH_DATE 
        ),
        FinalCalculations AS (
            SELECT *,
                AVG(OFFENSIV_INDEX) OVER() AS LIGA_AVG_OFFENSIV_INDEX,
                AVG(DEFENSIV_INDEX) OVER() AS LIGA_AVG_DEFENSIV_INDEX
            FROM FullTournamentData
        )
        SELECT * 
        FROM FinalCalculations
        ORDER BY MATCH_DATE ASC
    """

    df = pd.DataFrame()
    try:
        df = conn.query(query)
    except Exception as e:
        st.info(f"Bruger lokal CSV-fallback, da forbindelsen til databasen fejlede: {e}")

    if not df.empty:
        df.columns = [c.upper() for c in df.columns]
        # Live-forespørgslen lykkedes (helt eller delvist) - udfyld KUN de faktiske
        # huller pr. kamp fra CSV'en, i stedet for at overskrive alt. Samme logik
        # (og samme fil) som teams.py bruger - se data/sql/fallback.py.
        col_mapping = {
            'TOTALSCORINGATT': 'TOTALSCORINGATT',
            'ONTARGETSCORINGATT': 'ONTARGETSCORINGATT',
            'SHOTOFFTARGET': 'SHOTOFFTARGET',
            'BLOCKEDSCORINGATT': 'BLOCKEDSCORINGATT',
            'TOTALPASS': 'TOTALPASS',
            'ACCURATEPASS': 'ACCURATEPASS',
            'POSSESSIONPERCENTAGE': 'POSSESSIONPERCENTAGE',
            'WONCORNERS': 'WONCORNERS',
            'LOSTCORNERS': 'LOSTCORNERS',
            'TOTALTACKLE': 'TOTALTACKLE',
            'WONTACKLE': 'WONTACKLE',
            'TOTALCLEARANCE': 'TOTALCLEARANCE',
            'OUTFIELDERBLOCK': 'OUTFIELDERBLOCK',
            'FKFOULWON': 'FKFOULWON',
            'FKFOULLOST': 'FKFOULLOST',
            'SAVES': 'SAVES',
            'GOALSCONCEDED': 'GOALSCONCEDED',
            'CLEANSHEET': 'CLEANSHEET',
            'EXPECTEDGOALS': 'EXPECTEDGOALS',
        }
        df = fill_gaps_team_row(df, col_mapping)
    elif os.path.exists(FALLBACK_FILE):
        # Sidste udvej: forbindelsen fejlede helt, eller holdet har ingen kampe i
        # live-resultatet overhovedet - der er intet at hulfylde i, så her (og kun her)
        # bruges hele CSV-filen som erstatning.
        try:
            df = pd.read_csv(FALLBACK_FILE)
            if "TEAM_OPTAUUID" in df.columns:
                df = df[df["TEAM_OPTAUUID"] == team_opta_uuid]
        except Exception as csv_error:
            st.error(f"Fejl ved indlæsning af fallback CSV-fil: {csv_error}")

    if not df.empty:
        df.columns = [c.upper() for c in df.columns]
        if "MATCH_DATE" in df.columns:
            df["MATCH_DATE"] = pd.to_datetime(df["MATCH_DATE"], errors="coerce")
            df = df.sort_values("MATCH_DATE")
            df["MATCH_DATE"] = df["MATCH_DATE"].dt.strftime('%Y-%m-%d')
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)

    return df


@st.cache_data(ttl=1800, show_spinner="Henter ligadata fra Snowflake...")
def load_league_performance_data(calendar_uuid, wyid, filter_sql):
    """
    Henter samlet match- og statistikdata for hele ligaen (både Opta og WyScout)
    til Placering vs. Performance-siden med automatisk fallback til lokal CSV-fil.
    """
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    df_opta = pd.DataFrame()
    df_wy = pd.DataFrame()

    if conn:
        if calendar_uuid:
            try:
                df_opta = conn.query(f"""
                    SELECT * FROM {db}.OPTA_MATCHINFO 
                    WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
                    AND MATCH_DATE_FULL {filter_sql}
                """)
            except Exception as e:
                st.info(f"Kunne ikke hente OPTA-matchinfo fra databasen: {e}")

        if wyid:
            try:
                df_wy = conn.query(f"""
                    SELECT 
                        tm.TEAM_WYID, 
                        AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS,
                        AVG(opp_adv.GOALS) as GOALS_AGAINST,
                        AVG(md.PPDA) as PPDA, AVG(mp.PASSES) as PASSES
                    FROM {db}.WYSCOUT_TEAMMATCHES tm 
                    LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
                    LEFT JOIN {db}.WYSCOUT_TEAMMATCHES opp ON tm.MATCH_WYID = opp.MATCH_WYID AND tm.TEAM_WYID <> opp.TEAM_WYID
                    LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL opp_adv ON opp.MATCH_WYID = opp_adv.MATCH_WYID AND opp.TEAM_WYID = opp_adv.TEAM_WYID
                    LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
                    LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID
                    WHERE tm.COMPETITION_WYID = {wyid} 
                    AND tm.DATE {filter_sql} 
                    GROUP BY tm.TEAM_WYID
                """)
            except Exception as e:
                st.info(f"Kunne ikke hente WyScout data fra databasen: {e}")

    # Fallback hvis OPTA-data er tom
    if df_opta.empty and os.path.exists(FALLBACK_FILE):
        try:
            df_opta = pd.read_csv(FALLBACK_FILE)
        except Exception as csv_error:
            st.error(f"Fejl ved indlæsning af fallback CSV-fil: {csv_error}")

    if df_opta is not None and not df_opta.empty:
        df_opta.columns = [c.upper() for c in df_opta.columns]
        
    if df_wy is not None and not df_wy.empty:
        df_wy.columns = [c.upper() for c in df_wy.columns]
        
    return df_opta, df_wy


@st.cache_data(ttl=1800, show_spinner="Henter ligadata (kampe, xG og eventtal) fra Snowflake...")
def load_league_match_level_data(tournament_opta_uuid):
    conn = _get_snowflake_conn()
    if not conn:
        return pd.DataFrame()

    db = "KLUB_HVIDOVREIF.AXIS"

    query = f"""
        WITH MatchBase AS (
            SELECT 
                MATCH_OPTAUUID, MATCH_DATE_FULL, WEEK, MATCH_STATUS,
                CONTESTANTHOME_OPTAUUID, CONTESTANTHOME_NAME,
                CONTESTANTAWAY_OPTAUUID, CONTESTANTAWAY_NAME,
                TOTAL_HOME_SCORE, TOTAL_AWAY_SCORE, MATCH_LOCALTIME
            FROM {db}.OPTA_MATCHINFO
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{tournament_opta_uuid}'
        ),
        StatsPivot AS (
            SELECT 
                s.MATCH_OPTAUUID, s.CONTESTANT_OPTAUUID,
                MAX(CASE WHEN s.STAT_TYPE = 'possessionPercentage' THEN TRY_CAST(REPLACE(s.STAT_TOTAL, '%', '') AS FLOAT) END) AS POSSESSION,
                SUM(CASE WHEN s.STAT_TYPE = 'totalPass' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) ELSE 0 END) AS PASSES,
                SUM(CASE WHEN s.STAT_TYPE = 'totalScoringAtt' THEN TRY_CAST(s.STAT_TOTAL AS FLOAT) ELSE 0 END) AS SHOTS
            FROM {db}.OPTA_MATCHSTATS s
            JOIN MatchBase mb ON s.MATCH_OPTAUUID = mb.MATCH_OPTAUUID
            GROUP BY 1, 2
        ),
        AdvancedEvents AS (
            SELECT 
                MATCH_OPTAUUID, 
                EVENT_CONTESTANT_OPTAUUID,
                COUNT(CASE WHEN EVENT_X >= 81.0 AND EVENT_Y BETWEEN 20.0 AND 80.0 AND EVENT_TYPEID IN (1, 3, 4, 7, 13, 14, 15, 16, 17, 19, 24, 30) THEN 1 END) AS TOUCHES_IN_BOX,
                COUNT(CASE WHEN EVENT_TYPEID IN (13, 14, 15, 16) AND EVENT_X BETWEEN 83.0 AND 100.0 AND EVENT_Y BETWEEN 38.5 AND 61.5 THEN 1 END) AS DANGERZONE_SHOTS,
                COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 AND EVENT_X > 66.6 THEN 1 END) AS PASSES_FINAL_THIRD,
                COUNT(CASE WHEN EVENT_TYPEID = 1 AND EVENT_OUTCOME = 1 AND LEAD_X > (EVENT_X + 10) THEN 1 END) AS FORWARD_PASSES
            FROM (
                SELECT 
                    e.MATCH_OPTAUUID, 
                    e.EVENT_CONTESTANT_OPTAUUID, 
                    e.EVENT_TYPEID, 
                    e.EVENT_OUTCOME, 
                    e.EVENT_X, 
                    e.EVENT_Y,
                    LEAD(e.EVENT_X) OVER (
                        PARTITION BY e.MATCH_OPTAUUID, e.EVENT_CONTESTANT_OPTAUUID 
                        ORDER BY e.EVENT_TIMESTAMP, e.EVENT_EVENTID
                    ) AS LEAD_X
                FROM {db}.OPTA_EVENTS e
                JOIN MatchBase mb ON e.MATCH_OPTAUUID = mb.MATCH_OPTAUUID
            )
            GROUP BY 1, 2
        ),
        XGPivot AS (
            SELECT 
                x.MATCH_ID, x.CONTESTANT_OPTAUUID,
                SUM(CASE WHEN x.STAT_TYPE IN ('expectedGoals', 'expectedGoal') THEN TRY_CAST(x.STAT_VALUE AS FLOAT) ELSE 0 END) AS XG,
                SUM(CASE WHEN x.STAT_TYPE IN ('expectedGoalsNonpenalty', 'expectedGoalsNonPenalty') THEN TRY_CAST(x.STAT_VALUE AS FLOAT) ELSE 0 END) AS XGNP,
                SUM(CASE WHEN x.STAT_TYPE = 'bigChanceCreated' THEN TRY_CAST(x.STAT_VALUE AS FLOAT) ELSE 0 END) AS BIG_CHANCES
            FROM {db}.OPTA_MATCHEXPECTEDGOALS x
            JOIN MatchBase mb ON x.MATCH_ID = mb.MATCH_OPTAUUID
            GROUP BY 1, 2
        )
        SELECT 
            b.*,
            h.POSSESSION AS HOME_POSS, hx.XG AS HOME_XG, hx.XGNP AS HOME_XGNP, hx.BIG_CHANCES AS HOME_BIG_CHANCES, 
            h.PASSES AS HOME_PASSES, h.SHOTS AS HOME_SHOTS, 
            ae_h.FORWARD_PASSES AS HOME_FORWARD_PASSES, ae_h.DANGERZONE_SHOTS AS HOME_DZ_SHOTS, 
            ae_h.PASSES_FINAL_THIRD AS HOME_PASSES_FT, ae_h.TOUCHES_IN_BOX AS HOME_TOUCHES_IN_BOX,
            a.POSSESSION AS AWAY_POSS, ax.XG AS AWAY_XG, ax.XGNP AS AWAY_XGNP, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, 
            a.PASSES AS AWAY_PASSES, a.SHOTS AS AWAY_SHOTS, 
            ae_a.FORWARD_PASSES AS AWAY_FORWARD_PASSES, ae_a.DANGERZONE_SHOTS AS AWAY_DZ_SHOTS, 
            ae_a.PASSES_FINAL_THIRD AS AWAY_PASSES_FT, ae_a.TOUCHES_IN_BOX AS AWAY_TOUCHES_IN_BOX
        FROM MatchBase b
        LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
        LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
        LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
        LEFT JOIN AdvancedEvents ae_h ON b.MATCH_OPTAUUID = ae_h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = ae_h.EVENT_CONTESTANT_OPTAUUID
        LEFT JOIN AdvancedEvents ae_a ON b.MATCH_OPTAUUID = ae_a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = ae_a.EVENT_CONTESTANT_OPTAUUID
    """

    try:
        df = conn.query(query) if hasattr(conn, "query") else pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Fejl ved hentning af ligadata: {e}")
        return pd.DataFrame()

    if df is not None and not df.empty:
        df.columns = [str(c).upper() for c in df.columns]
        
        # Sørg for at fallback-data (kampe_fallback.csv) automatisk lapper huller
        col_mapping = {
            'POSSESSIONPERCENTAGE': 'POSS',
            'TOTALPASS': 'PASSES',
            'TOTALSCORINGATT': 'SHOTS',
            'EXPECTEDGOALS': 'XG',
            'EXPECTEDGOALSNONPENALTY': 'XGNP',
            'BIGCHANCECREATED': 'BIG_CHANCES'
        }
        df = fill_gaps_side_aware(df, col_mapping)

    return df if df is not None else pd.DataFrame()
