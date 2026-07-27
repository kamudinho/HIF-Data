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
                    SUM(CASE WHEN STAT_TYPE = 'wonTackle' THEN STAT_TOTAL ELSE 0 END) AS TACKLES_WON,
                    SUM(CASE WHEN STAT_TYPE = 'totalFoul' THEN STAT_TOTAL ELSE 0 END) AS FOULS,
                    SUM(CASE WHEN STAT_TYPE = 'yellowCard' THEN STAT_TOTAL ELSE 0 END) AS YELLOW_CARDS,
                    SUM(CASE WHEN STAT_TYPE = 'corner' THEN STAT_TOTAL ELSE 0 END) AS CORNERS
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
                    SUM(CASE WHEN EVENT_TYPEID = 7 THEN 1 ELSE 0 END) AS TACKLES_DEF,
                    SUM(CASE WHEN EVENT_TYPEID = 8 THEN 1 ELSE 0 END) AS INTERCEPTIONS,
                    AVG(EVENT_TIMEMIN) AS AVG_EVENT_TIMEMIN
                FROM {DB}.OPTA_EVENTS
                GROUP BY 1, 2
            )
            SELECT 
                b.*,
                h.POSSESSION AS HOME_POSS, h.PASSES AS HOME_PASSES, h.ACCURATE_PASSES AS HOME_ACC_PASSES,
                h.SHOTS AS HOME_SHOTS, h.SHOTS_ON_TARGET AS HOME_SHOTS_ON_TARGET, h.TACKLES_WON AS HOME_TACKLES,
                h.FOULS AS HOME_FOULS, h.YELLOW_CARDS AS HOME_YELLOW, h.CORNERS AS HOME_CORNERS,
                hx.XG AS HOME_XG, hx.BIG_CHANCES AS HOME_BIG_CHANCES, hx.PREVENTED_GOALS AS HOME_PREV_GOALS, 
                h_box.CALCULATED_BOX_ENTRIES AS HOME_BOX_ENTRIES,
                h_ft.FT_PASSES_SUCCESSFUL AS HOME_FT_SUCCESS, h_ft.FT_PASSES_UNSUCCESSFUL AS HOME_FT_UNSUCCESS,
                h_ft.FT_SHOTS_PRODUCED AS HOME_FT_SHOTS, h_ft.FT_GOALS AS HOME_FT_GOALS,
                h_adv.FOULS_COMMITTED AS HOME_FOULS_COMMITTED, h_adv.TACKLES_DEF AS HOME_TACKLES_DEF, h_adv.INTERCEPTIONS AS HOME_INTERCEPTIONS,
                
                a.POSSESSION AS AWAY_POSS, a.PASSES AS AWAY_PASSES, a.ACCURATE_PASSES AS AWAY_ACC_PASSES,
                a.SHOTS AS AWAY_SHOTS, a.SHOTS_ON_TARGET AS AWAY_SHOTS_ON_TARGET, a.TACKLES_WON AS AWAY_TACKLES,
                a.FOULS AS AWAY_FOULS, a.YELLOW_CARDS AS AWAY_YELLOW, a.CORNERS AS AWAY_CORNERS,
                ax.XG AS AWAY_XG, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, ax.PREVENTED_GOALS AS AWAY_PREV_GOALS, 
                a_box.CALCULATED_BOX_ENTRIES AS AWAY_BOX_ENTRIES,
                a_ft.FT_PASSES_SUCCESSFUL AS AWAY_FT_SUCCESS, a_ft.FT_PASSES_UNSUCCESSFUL AS AWAY_FT_UNSUCCESS,
                a_ft.FT_SHOTS_PRODUCED AS AWAY_FT_SHOTS, a_ft.FT_GOALS AS AWAY_FT_GOALS,
                a_adv.FOULS_COMMITTED AS AWAY_FOULS_COMMITTED, a_adv.TACKLES_DEF AS AWAY_TACKLES_DEF, a_adv.INTERCEPTIONS AS AWAY_INTERCEPTIONS
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
            
            a_passes_val = float(row.get('AWAY_PASSES', 0) or 0)
            h_def_actions = float(row.get('HOME_TACKLES_DEF', 0) or 0) + float(row.get('HOME_INTERCEPTIONS', 0) or 0) + float(row.get('HOME_FOULS_COMMITTED', 0) or 0)
            h_ppda = (a_passes_val / h_def_actions) if h_def_actions > 0 else 0.0

            a_passes = float(row.get('AWAY_PASSES', 0) or 0)
            a_acc = float(row.get('AWAY_ACC_PASSES', 0) or 0)
            a_pass_pct = (a_acc / a_passes * 100.0) if a_passes > 0 else 0.0
            
            h_passes_val = float(row.get('HOME_PASSES', 0) or 0)
            a_def_actions = float(row.get('AWAY_TACKLES_DEF', 0) or 0) + float(row.get('AWAY_INTERCEPTIONS', 0) or 0) + float(row.get('AWAY_FOULS_COMMITTED', 0) or 0)
            a_ppda = (h_passes_val / a_def_actions) if a_def_actions > 0 else 0.0

            h_poss_pct = float(pd.to_numeric(row.get('HOME_POSS'), errors='coerce') or 50.0)
            a_poss_pct = float(pd.to_numeric(row.get('AWAY_POSS'), errors='coerce') or 50.0)

            match_rows.append({
                'TEAM_UUID': h_uuid,
                'RESULTAT': 'Sejr' if h_score > a_score else ('Uafgjort' if h_score == a_score else 'Nederlag'),
                'POSS': h_poss_pct,
                'PASSES': h_passes,
                'PASS_PCT': h_pass_pct,
                'SHOTS': pd.to_numeric(row.get('HOME_SHOTS'), errors='coerce'),
                'SHOTS_ON_TARGET': pd.to_numeric(row.get('HOME_SHOTS_ON_TARGET'), errors='coerce'),
                'TACKLES': pd.to_numeric(row.get('HOME_TACKLES'), errors='coerce'),
                'FOULS': pd.to_numeric(row.get('HOME_FOULS'), errors='coerce'),
                'YELLOW': pd.to_numeric(row.get('HOME_YELLOW'), errors='coerce'),
                'CORNERS': pd.to_numeric(row.get('HOME_CORNERS'), errors='coerce'),
                'XG': pd.to_numeric(row.get('HOME_XG'), errors='coerce'),
                'BIG_CHANCES': pd.to_numeric(row.get('HOME_BIG_CHANCES'), errors='coerce'),
                'PREv_GOALS': pd.to_numeric(row.get('HOME_PREV_GOALS'), errors='coerce'),
                'BOX_ENTRIES': pd.to_numeric(row.get('HOME_BOX_ENTRIES'), errors='coerce'),
                'FT_SUCCESS': pd.to_numeric(row.get('HOME_FT_SUCCESS'), errors='coerce'),
                'FT_UNSUCCESS': pd.to_numeric(row.get('HOME_FT_UNSUCCESS'), errors='coerce'),
                'FT_SHOTS': pd.to_numeric(row.get('HOME_FT_SHOTS'), errors='coerce'),
                'FT_GOALS': pd.to_numeric(row.get('HOME_FT_GOALS'), errors='coerce'),
                'PPDA': h_ppda,
                'BALL_TIME': (h_poss_pct / 100.0) * 90.0
            })
            match_rows.append({
                'TEAM_UUID': a_uuid,
                'RESULTAT': 'Sejr' if a_score > h_score else ('Uafgjort' if a_score == h_score else 'Nederlag'),
                'POSS': a_poss_pct,
                'PASSES': a_passes,
                'PASS_PCT': a_pass_pct,
                'SHOTS': pd.to_numeric(row.get('AWAY_SHOTS'), errors='coerce'),
                'SHOTS_ON_TARGET': pd.to_numeric(row.get('AWAY_SHOTS_ON_TARGET'), errors='coerce'),
                'TACKLES': pd.to_numeric(row.get('AWAY_TACKLES'), errors='coerce'),
                'FOULS': pd.to_numeric(row.get('AWAY_FOULS'), errors='coerce'),
                'YELLOW': pd.to_numeric(row.get('AWAY_YELLOW'), errors='coerce'),
                'CORNERS': pd.to_numeric(row.get('AWAY_CORNERS'), errors='coerce'),
                'XG': pd.to_numeric(row.get('AWAY_XG'), errors='coerce'),
                'BIG_CHANCES': pd.to_numeric(row.get('AWAY_BIG_CHANCES'), errors='coerce'),
                'PREv_GOALS': pd.to_numeric(row.get('AWAY_PREV_GOALS'), errors='coerce'),
                'BOX_ENTRIES': pd.to_numeric(row.get('AWAY_BOX_ENTRIES'), errors='coerce'),
                'FT_SUCCESS': pd.to_numeric(row.get('AWAY_FT_SUCCESS'), errors='coerce'),
                'FT_UNSUCCESS': pd.to_numeric(row.get('AWAY_FT_UNSUCCESS'), errors='coerce'),
                'FT_SHOTS': pd.to_numeric(row.get('AWAY_FT_SHOTS'), errors='coerce'),
                'FT_GOALS': pd.to_numeric(row.get('AWAY_FT_GOALS'), errors='coerce'),
                'PPDA': a_ppda,
                'BALL_TIME': (a_poss_pct / 100.0) * 90.0
            })

        df_perf = pd.DataFrame(match_rows)
        team_perf = df_perf.dropna(subset=['TEAM_UUID'])

        if not team_perf.empty:
            cols_to_mean = [
                'POSS', 'PASSES', 'PASS_PCT', 'SHOTS', 'SHOTS_ON_TARGET', 'TACKLES', 
                'FOULS', 'YELLOW', 'CORNERS', 'XG', 'BIG_CHANCES', 'PREv_GOALS', 
                'BOX_ENTRIES', 'FT_SUCCESS', 'FT_UNSUCCESS', 'FT_SHOTS', 'FT_GOALS',
                'PPDA', 'BALL_TIME'
            ]
            summary_table = team_perf.groupby('RESULTAT')[cols_to_mean].mean().reindex(['Sejr', 'Uafgjort', 'Nederlag']).T
            
            summary_table.index = [
                'Boldbesiddelse (%)', 
                'Afleveringer (Total)', 
                'Pasningsprocent (%)', 
                'Afslutninger (Total)', 
                'Afslutninger (Inden for ramme)', 
                'Vundne Tacklinger', 
                'Frispark begået', 
                'Gule kort', 
                'Hjørnespark', 
                'xG (Forventede Mål)', 
                'Store Chancer', 
                'Mål indkasseret',
                'Box Entries',
                'Final Third: Succesfulde Afleveringer',
                'Final Third: Afleveringer',
                'Final Third: Afslutninger',
                'Final Third: Mål',
                'PPDA (Passes Per Defensive Action)',
                'Effektiv tid med bolden (min)'
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
                st.markdown("Alle gennemsnitlige præstationsmål fordelt på kampens udfald (inkl. beregnede hændelser)")
                
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
                    st.markdown("##### 🔴 OPBYGNINGSSPIL")
                    st.markdown(f"- **Pasningsprocent:** {get_val('Pasningsprocent (%)')} (Mål: >78%)")
                    st.markdown(f"- **Afleveringer (Total):** {get_val('Afleveringer (Total)')}")
                    st.markdown(f"- **Boldbesiddelse:** {get_val('Boldbesiddelse (%)')}%")

                with col2:
                    st.markdown("##### 🔴 AVSLUTNINGSSPIL")
                    st.markdown(f"- **xG (Forventede Mål):** {get_val('xG (Forventede Mål)')}")
                    st.markdown(f"- **Store Chancer:** {get_val('Store Chancer')}")
                    st.markdown(f"- **Box Entries:** {get_val('Box Entries')}")
                    st.markdown(f"- **FT Succesfulde Afleveringer:** {get_val('Final Third: Succesfulde Afleveringer')}")

                with col3:
                    st.markdown("##### 🔴 FORSVARSSPIL")
                    st.markdown(f"- **Mål indkasseret:** {get_val('Mål indkasseret')}")
                    st.markdown(f"- **Vundne Tacklinger:** {get_val('Vundne Tacklinger')}")
                    st.markdown(f"- **Frispark begået:** {get_val('Frispark begået')}")
                    st.markdown(f"- **Gule kort:** {get_val('Gule kort')}")

                with col4:
                    st.markdown("##### 🔴 EROBRINGSSPIL")
                    st.markdown(f"- **PPDA:** {get_val('PPDA (Passes Per Defensive Action)')} (Mål: <13)")
                    st.markdown(f"- **Effektiv tid med bolden:** {get_val('Effektiv tid med bolden (min)')} min")
                    st.markdown(f"- **Hjørnespark:** {get_val('Hjørnespark')}")

        else:
            st.warning("Ikke nok data tilgængelig.")

    except Exception as e:
        st.error(f"Der opstod en fejl på siden: {e}")
