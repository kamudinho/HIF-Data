import streamlit as st
import pandas as pd

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
                    SUM(CASE WHEN STAT_TYPE = 'preventedGoals' THEN STAT_VALUE ELSE 0 END) AS PREVENTED_GOALS,
                    SUM(CASE WHEN STAT_TYPE IN ('entryBoxSuccess', 'boxEntrySuccess', 'successfulBoxEntry') THEN STAT_VALUE ELSE 0 END) AS BOX_ENTRIES
                FROM {DB}.OPTA_MATCHEXPECTEDGOALS
                GROUP BY 1, 2
            )
            SELECT 
                b.*,
                h.POSSESSION AS HOME_POSS, h.PASSES AS HOME_PASSES, h.ACCURATE_PASSES AS HOME_ACC_PASSES,
                h.SHOTS AS HOME_SHOTS, h.SHOTS_ON_TARGET AS HOME_SHOTS_ON_TARGET, h.TACKLES_WON AS HOME_TACKLES,
                h.FOULS AS HOME_FOULS, h.YELLOW_CARDS AS HOME_YELLOW, h.CORNERS AS HOME_CORNERS,
                hx.XG AS HOME_XG, hx.BIG_CHANCES AS HOME_BIG_CHANCES, hx.PREVENTED_GOALS AS HOME_PREV_GOALS, hx.BOX_ENTRIES AS HOME_BOX_ENTRIES,
                
                a.POSSESSION AS AWAY_POSS, a.PASSES AS AWAY_PASSES, a.ACCURATE_PASSES AS AWAY_ACC_PASSES,
                a.SHOTS AS AWAY_SHOTS, a.SHOTS_ON_TARGET AS AWAY_SHOTS_ON_TARGET, a.TACKLES_WON AS AWAY_TACKLES,
                a.FOULS AS AWAY_FOULS, a.YELLOW_CARDS AS AWAY_YELLOW, a.CORNERS AS AWAY_CORNERS,
                ax.XG AS AWAY_XG, ax.BIG_CHANCES AS AWAY_BIG_CHANCES, ax.PREVENTED_GOALS AS AWAY_PREV_GOALS, ax.BOX_ENTRIES AS AWAY_BOX_ENTRIES
            FROM MatchBase b
            LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
            LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
            LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
            LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
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
            
            h_passes = row.get('HOME_PASSES', 0) or 0
            h_acc = row.get('HOME_ACC_PASSES', 0) or 0
            h_pass_pct = (h_acc / h_passes * 100) if h_passes > 0 else 0

            a_passes = row.get('AWAY_PASSES', 0) or 0
            a_acc = row.get('AWAY_ACC_PASSES', 0) or 0
            a_pass_pct = (a_acc / a_passes * 100) if a_passes > 0 else 0

            match_rows.append({
                'TEAM_UUID': h_uuid,
                'RESULTAT': 'Sejr' if h_score > a_score else ('Uafgjort' if h_score == a_score else 'Nederlag'),
                'POSS': pd.to_numeric(row.get('HOME_POSS'), errors='coerce'),
                'PASSES': pd.to_numeric(h_passes, errors='coerce'),
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
                'BOX_ENTRIES': pd.to_numeric(row.get('HOME_BOX_ENTRIES'), errors='coerce')
            })
            match_rows.append({
                'TEAM_UUID': a_uuid,
                'RESULTAT': 'Sejr' if a_score > h_score else ('Uafgjort' if a_score == h_score else 'Nederlag'),
                'POSS': pd.to_numeric(row.get('AWAY_POSS'), errors='coerce'),
                'PASSES': pd.to_numeric(a_passes, errors='coerce'),
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
                'BOX_ENTRIES': pd.to_numeric(row.get('AWAY_BOX_ENTRIES'), errors='coerce')
            })

        df_perf = pd.DataFrame(match_rows)
        team_perf = df_perf.dropna(subset=['TEAM_UUID'])

        if not team_perf.empty:
            cols_to_mean = ['POSS', 'PASSES', 'PASS_PCT', 'SHOTS', 'SHOTS_ON_TARGET', 'TACKLES', 'FOULS', 'YELLOW', 'CORNERS', 'XG', 'BIG_CHANCES', 'PREv_GOALS', 'BOX_ENTRIES']
            summary_table = team_perf.groupby('RESULTAT')[cols_to_mean].mean().reindex(['Sejr', 'Uafgjort', 'Nederlag']).T
            
            summary_table.index = [
                'Boldbesiddelse (%)', 
                'Afleveringer (Total)', 
                'Pasningsprocent (%) [Mål: >78%]', 
                'Afslutninger (Total)', 
                'Afslutninger (Inden for ramme)', 
                'Vundne Tacklinger', 
                'Frispark begået', 
                'Gule kort', 
                'Hjørnespark', 
                'xG (Forventede Mål)', 
                'Store Chancer', 
                'Forhindrede Mål (Prevented Goals)',
                'Box Entries (Feltindsættelser)'
            ]

            # Farvekodningsfunktion til at fremhæve målsætninger i Sejr-kolonnen
            def color_cells(val, row_name):
                try:
                    v = float(val)
                except:
                    return ''
                
                if "Pasningsprocent" in row_name and v >= 78:
                    return 'background-color: #d4edda;'
                elif "Succesfulde pasninger" in row_name and v >= 445:
                    return 'background-color: #d4edda;'
                return ''

            tab1, tab2 = st.tabs(["Datagrundlag", "Winning Performance Model"])

            with tab1:
                st.markdown("#### Alle gennemsnitlige præstationsmål fordelt på kampens udfald")
                st.dataframe(
                    summary_table.style.format("{:.2f}").background_gradient(cmap="Greens", axis=1),
                    use_container_width=True
                )
                st.info(f"💡 Tabellen viser alle metrikker (inkl. Box Entries) opdelt efter Sejr, Uafgjort og Nederlag for sæson {SEASONNAME}.")

            with tab2:
                st.markdown("#### Winning Performance Model (Fase-opdelt målstruktur)")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown("##### 🔴 OPBYGNINGSSPIL")
                    st.markdown("- **Pasningsprocent:** >78%")
                    st.markdown("- **Progression from 1/3:** >75%")
                    st.markdown("- **XT (Threat):** >1,4")
                    st.markdown("- **Succesfulde pasninger:** >445")
                    st.markdown("- **<6 aktioner** på modstanders halvdel når midterlinje passeres")

                with col2:
                    st.markdown("##### 🔴 AVSLUTNINGSSPIL")
                    st.markdown("- **Avg xG pr. afslutning:** >0,11")
                    st.markdown("- **xG / Box Entry:** >0,15")
                    st.markdown("- **Pasninger til 10ere på off. tredjedel:** >12")
                    st.markdown("- **Box entries efter retvendt 10er:** >4")
                    st.markdown("- **Berøringer i feltet:** >10")
                    st.markdown("- **Succesfulde box entries (indlæg + pasning):** >12")

                with col3:
                    st.markdown("##### 🔴 FORSVARSSPIL")
                    st.markdown("- **Avg xG imod:** <1,0")
                    st.markdown("- **xG / Box entries imod:** <0,09")
                    st.markdown("- **Unsuccesful box entries fra central korridor:** <60%")
                    st.markdown("- **Berøringer i feltet imod:** <9")
                    st.markdown("- **Succesfulde pasninger imod:** <74%")
                    st.markdown("- **Box entries imod:** <8")

                with col4:
                    st.markdown("##### 🔴 EROBRINGSSPIL")
                    st.markdown("- **PPDA:** <13")
                    st.markdown("- **Fasthold erobring 2/3:** [Målsætning]")
                    st.markdown("- **Tid modstanderen har bolden:** <11 sek")

        else:
            st.warning("Ikke nok data tilgængelig.")

    except Exception as e:
        st.error(f"Der opstod en fejl på siden: {e}")
