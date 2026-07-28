import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side():
    try:
        st.caption("1. Division — Over- og Underpræstation mod Baseline")
        
        from data.data_load import _get_snowflake_conn
        conn = _get_snowflake_conn()
        
        if not conn:
            st.error("Kunne ikke oprette forbindelse til Snowflake.")
            return

        DB = "KLUB_HVIDOVREIF.AXIS"
        SEASONNAME = "2025/2026"
        
        # SQL der henter hold og deres statistikker for 1. Division (komp ID 328)
        sql = f"""
            WITH MatchBase AS (
                SELECT 
                    m.MATCH_OPTAUUID, m.MATCH_STATUS,
                    m.CONTESTANTHOME_OPTAUUID, m.CONTESTANTAWAY_OPTAUUID,
                    h_team.NAME AS HOME_TEAM_NAME,
                    a_team.NAME AS AWAY_TEAM_NAME
                FROM {DB}.OPTA_MATCHINFO m
                LEFT JOIN {DB}.OPTA_CONTESTANT h_team ON m.CONTESTANTHOME_OPTAUUID = h_team.CONTESTANT_OPTAUUID
                LEFT JOIN {DB}.OPTA_CONTESTANT a_team ON m.CONTESTANTAWAY_OPTAUUID = a_team.CONTESTANT_OPTAUUID
                WHERE m.COMPETITION_OPTAUUID IN (
                    SELECT COMPETITION_OPTAUUID FROM {DB}.OPTA_TOURNAMENTCALENDAR 
                    WHERE COMPETITION_WYID = 328 AND SEASONNAME = '{SEASONNAME}'
                )
            ),
            StatsPivot AS (
                SELECT 
                    MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                    SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) AS GOALS,
                    SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS,
                    SUM(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS_ON_TARGET,
                    SUM(CASE WHEN STAT_TYPE = 'cornerTaken' THEN STAT_TOTAL ELSE 0 END) AS CORNERS,
                    SUM(CASE WHEN STAT_TYPE = 'totalFoul' THEN STAT_TOTAL ELSE 0 END) AS FOULS,
                    SUM(CASE WHEN STAT_TYPE = 'yellowCard' THEN STAT_TOTAL ELSE 0 END) AS YELLOW_CARDS,
                    SUM(CASE WHEN STAT_TYPE = 'totalTackle' THEN STAT_TOTAL ELSE 0 END) AS TACKLES,
                    SUM(CASE WHEN STAT_TYPE = 'totalClearance' THEN STAT_TOTAL ELSE 0 END) AS CLEARANCES,
                    SUM(CASE WHEN STAT_TYPE = 'saves' THEN STAT_TOTAL ELSE 0 END) AS SAVES
                FROM {DB}.OPTA_MATCHSTATS
                GROUP BY 1, 2
            ),
            XGPivot AS (
                SELECT 
                    MATCH_ID, CONTESTANT_OPTAUUID,
                    SUM(CASE WHEN STAT_TYPE IN ('expectedGoals', 'expectedGoal') THEN STAT_VALUE ELSE 0 END) AS XG
                FROM {DB}.OPTA_MATCHEXPECTEDGOALS
                GROUP BY 1, 2
            )
            SELECT 
                b.MATCH_OPTAUUID, b.MATCH_STATUS,
                b.HOME_TEAM_NAME, b.AWAY_TEAM_NAME,
                b.CONTESTANTHOME_OPTAUUID, b.CONTESTANTAWAY_OPTAUUID,
                
                h.GOALS AS HOME_GOALS, h.SHOTS AS HOME_SHOTS, h.SHOTS_ON_TARGET AS HOME_SHOTS_ON_TARGET,
                h.CORNERS AS HOME_CORNERS, h.FOULS AS HOME_FOULS, h.YELLOW_CARDS AS HOME_YELLOW,
                h.TACKLES AS HOME_TACKLES, h.CLEARANCES AS HOME_CLEARANCES, h.SAVES AS HOME_SAVES,
                hx.XG AS HOME_XG,
                
                a.GOALS AS AWAY_GOALS, a.SHOTS AS AWAY_SHOTS, a.SHOTS_ON_TARGET AS AWAY_SHOTS_ON_TARGET,
                a.CORNERS AS AWAY_CORNERS, a.FOULS AS AWAY_FOULS, a.YELLOW_CARDS AS AWAY_YELLOW,
                a.TACKLES AS AWAY_TACKLES, a.CLEARANCES AS AWAY_CLEARANCES, a.SAVES AS AWAY_SAVES,
                ax.XG AS AWAY_XG
            FROM MatchBase b
            LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
            LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
            LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
            LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
        """

        with st.spinner("Henter 1. divisionsdata..."):
            df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

            if df_matches is None or df_matches.empty:
                st.warning("Ingen data fundet for 1. division.")
                return

            df_matches.columns = [str(c).upper() for c in df_matches.columns]
            played = df_matches[df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()

            team_rows = []
            for _, row in played.iterrows():
                # Hjemmehold
                if pd.notnull(row.get('HOME_TEAM_NAME')):
                    team_rows.append({
                        'TEAM': row['HOME_TEAM_NAME'],
                        'GOALS': pd.to_numeric(row.get('HOME_GOALS'), errors='coerce') or 0,
                        'SHOTS': pd.to_numeric(row.get('HOME_SHOTS'), errors='coerce') or 0,
                        'SHOTS_ON_TARGET': pd.to_numeric(row.get('HOME_SHOTS_ON_TARGET'), errors='coerce') or 0,
                        'XG': pd.to_numeric(row.get('HOME_XG'), errors='coerce') or 0.0,
                        'CORNERS': pd.to_numeric(row.get('HOME_CORNERS'), errors='coerce') or 0,
                        'FOULS': pd.to_numeric(row.get('HOME_FOULS'), errors='coerce') or 0,
                        'YELLOW_CARDS': pd.to_numeric(row.get('HOME_YELLOW'), errors='coerce') or 0,
                        'TACKLES': pd.to_numeric(row.get('HOME_TACKLES'), errors='coerce') or 0,
                        'SAVES': pd.to_numeric(row.get('HOME_SAVES'), errors='coerce') or 0
                    })
                # Udehold
                if pd.notnull(row.get('AWAY_TEAM_NAME')):
                    team_rows.append({
                        'TEAM': row['AWAY_TEAM_NAME'],
                        'GOALS': pd.to_numeric(row.get('AWAY_GOALS'), errors='coerce') or 0,
                        'SHOTS': pd.to_numeric(row.get('AWAY_SHOTS'), errors='coerce') or 0,
                        'SHOTS_ON_TARGET': pd.to_numeric(row.get('AWAY_SHOTS_ON_TARGET'), errors='coerce') or 0,
                        'XG': pd.to_numeric(row.get('AWAY_XG'), errors='coerce') or 0.0,
                        'CORNERS': pd.to_numeric(row.get('AWAY_CORNERS'), errors='coerce') or 0,
                        'FOULS': pd.to_numeric(row.get('AWAY_FOULS'), errors='coerce') or 0,
                        'YELLOW_CARDS': pd.to_numeric(row.get('AWAY_YELLOW'), errors='coerce') or 0,
                        'TACKLES': pd.to_numeric(row.get('AWAY_TACKLES'), errors='coerce') or 0,
                        'SAVES': pd.to_numeric(row.get('AWAY_SAVES'), errors='coerce') or 0
                    })

            df_teams = pd.DataFrame(team_rows)
            if df_teams.empty:
                st.warning("Ikke nok data til at generere tabellen.")
                return

            # Aggreger pr. hold
            agg_df = df_teams.groupby('TEAM').sum(numeric_only=True).reset_index()
            
            # Tilføj kampe spillet for at kunne lave gennemsnit pr kamp hvis ønsket, ellers totaler
            match_counts = df_teams.groupby('TEAM').size().reset_index(name='MATCHES')
            agg_df = pd.merge(agg_df, match_counts, on='TEAM')

            # ----------------- DROPDOWN TIL VALG AF KATEGORI -----------------
            metric_labels = {
                "Mål vs. Skud-baseline (Faktiske mål minus forventede mål baseret på skudvolumen)": "GOALS_VS_BASELINE",
                "xG vs. Faktiske Mål (Afslutningskvalitet)": "XG_VS_GOALS",
                "Skud på mål (Total)": "SHOTS_ON_TARGET",
                "Hjørnespark": "CORNERS",
                "Tacklinger": "TACKLES",
                "Frispark": "FOULS",
                "Gule kort": "YELLOW_CARDS",
                "Redninger": "SAVES"
            }

            selected_label = st.selectbox("Vælg parameter:", list(metric_labels.keys()))
            metric_key = metric_labels[selected_label]

            # Beregn baseline-forskelle baseret på valgt kategori
            if metric_key == "GOALS_VS_BASELINE":
                # Ligaens samlede konverteringsrate (Mål / Skud)
                total_league_goals = agg_df['GOALS'].sum()
                total_league_shots = agg_df['SHOTS'].sum()
                league_conversion = total_league_goals / total_league_shots if total_league_shots > 0 else 0.1
                
                # Forventede mål ud fra holdets egne skud * ligaens konverteringsrate
                agg_df['BASELINE_VAL'] = agg_df['SHOTS'] * league_conversion
                agg_df['DIFF'] = agg_df['GOALS'] - agg_df['BASELINE_VAL']
                chart_title = "Mål over eller under en skud-volumen baseline"
                xaxis_title = "mål vs. skud-volumen baseline"

            elif metric_key == "XG_VS_GOALS":
                agg_df['DIFF'] = agg_df['GOALS'] - agg_df['XG']
                chart_title = "Faktiske mål minus xG (Over/underpræstation på afslutninger)"
                xaxis_title = "mål minus xG"

            else:
                # Generel baseline: Holdets værdi minus ligaens gennemsnit pr. kamp * holdets kampe
                league_avg_per_match = agg_df[metric_key].sum() / agg_df['MATCHES'].sum()
                agg_df['BASELINE_VAL'] = agg_df['MATCHES'] * league_avg_per_match
                agg_df['DIFF'] = agg_df[metric_key] - agg_df['BASELINE_VAL']
                chart_title = f"{selected_label} vs. Liga-gennemsnit"
                xaxis_title = f"forskel i forhold til gennemsnit"

            # Sorter data (højest til lavest)
            agg_df = agg_df.sort_values(by='DIFF', ascending=True)
            
            # Tilføj farve-kolonne (positiv = orange/gul, negativ = blå ligesom i eksemplet)
            agg_df['COLOR_TYPE'] = agg_df['DIFF'].apply(lambda x: 'Overpræsterer' if x >= 0 else 'Underpræsterer')

            # Opret Plotly horisontal søjlediagram
            fig = px.bar(
                agg_df,
                x='DIFF',
                y='TEAM',
                orientation='h',
                title=chart_title,
                color='COLOR_TYPE',
                color_discrete_map={
                    'Overpræsterer': '#f39c12', # Orange
                    'Underpræsterer': '#2980b9'  # Blå
                },
                text_auto='.1f'
            )

            fig.update_layout(
                xaxis_title=xaxis_title,
                yaxis_title="",
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='gray'),
                title_font=dict(size=18, color='black')
            )
            
            fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eaeaea')
            fig.update_yaxes(showgrid=False)

            st.plotly_chart(fig, use_container_width=True)

            # Ekstra info-tekst
            st.info("Højre for nul = Flere mål/værdi end volumen alene tilsiger; venstre = Færre. Analysen er sat op specifikt til NordicBet Liga (1. division).")

    except Exception as e:
        st.error(f"Fejl ved indlæsning af siden: {e}")
