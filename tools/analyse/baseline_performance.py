import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from data.utils.team_mapping import SEASONS, COMPETITION_NAME

def vis_side(df_events=None, kamp=None, hold_map=None):
    try:
        from data.data_load import _get_snowflake_conn
        conn = _get_snowflake_conn()
        
        if not conn:
            st.error("Kunne ikke oprette forbindelse til Snowflake.")
            return

        DB = "KLUB_HVIDOVREIF.AXIS"
        
        valgt_saeson = st.session_state.get("saeson_select", "2025/2026")
        competition_uuid = SEASONS.get(valgt_saeson, {}).get(COMPETITION_NAME, "dyjr458hcmrcy87fsabfsy87o")
        
        sql = f"""
            WITH MatchBase AS (
                SELECT 
                    MATCH_OPTAUUID, MATCH_STATUS,
                    CONTESTANTHOME_OPTAUUID, CONTESTANTAWAY_OPTAUUID,
                    CONTESTANTHOME_NAME AS HOME_TEAM_NAME,
                    CONTESTANTAWAY_NAME AS AWAY_TEAM_NAME
                FROM {DB}.OPTA_MATCHINFO
                WHERE TOURNAMENTCALENDAR_OPTAUUID = '{competition_uuid}'
            ),
            StatsPivot AS (
                SELECT 
                    MATCH_OPTAUUID, CONTESTANT_OPTAUUID,
                    SUM(CASE WHEN STAT_TYPE = 'goals' THEN STAT_TOTAL ELSE 0 END) AS GOALS,
                    SUM(CASE WHEN STAT_TYPE = 'totalScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS,
                    SUM(CASE WHEN STAT_TYPE = 'ontargetScoringAtt' THEN STAT_TOTAL ELSE 0 END) AS SHOTS_ON_TARGET,
                    SUM(CASE WHEN STAT_TYPE = 'cornerTaken' THEN STAT_TOTAL ELSE 0 END) AS CORNERS,
                    SUM(CASE WHEN STAT_TYPE = 'totalFoul' THEN STAT_TOTAL ELSE 0 END) AS FOULS,
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
                h.CORNERS AS HOME_CORNERS, h.FOULS AS HOME_FOULS,
                h.TACKLES AS HOME_TACKLES, h.CLEARANCES AS HOME_CLEARANCES, h.SAVES AS HOME_SAVES,
                hx.XG AS HOME_XG,
                
                a.GOALS AS AWAY_GOALS, a.SHOTS AS AWAY_SHOTS, a.SHOTS_ON_TARGET AS AWAY_SHOTS_ON_TARGET,
                a.CORNERS AS AWAY_CORNERS, a.FOULS AS AWAY_FOULS,
                a.TACKLES AS AWAY_TACKLES, a.CLEARANCES AS AWAY_CLEARANCES, a.SAVES AS AWAY_SAVES,
                ax.XG AS AWAY_XG
            FROM MatchBase b
            LEFT JOIN StatsPivot h ON b.MATCH_OPTAUUID = h.MATCH_OPTAUUID AND b.CONTESTANTHOME_OPTAUUID = h.CONTESTANT_OPTAUUID
            LEFT JOIN StatsPivot a ON b.MATCH_OPTAUUID = a.MATCH_OPTAUUID AND b.CONTESTANTAWAY_OPTAUUID = a.CONTESTANT_OPTAUUID
            LEFT JOIN XGPivot hx ON b.MATCH_OPTAUUID = hx.MATCH_ID AND b.CONTESTANTHOME_OPTAUUID = hx.CONTESTANT_OPTAUUID
            LEFT JOIN XGPivot ax ON b.MATCH_OPTAUUID = ax.MATCH_ID AND b.CONTESTANTAWAY_OPTAUUID = ax.CONTESTANT_OPTAUUID
        """

        with st.spinner("Henter 1. divisionsdata til analyse..."):
            df_matches = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)

            if df_matches is None or df_matches.empty:
                st.warning("Ingen data fundet for 1. division i den valgte sæson.")
                return

            df_matches.columns = [str(c).upper() for c in df_matches.columns]
            played = df_matches[df_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)].copy()

            team_rows = []
            for _, row in played.iterrows():
                h_name = row.get('HOME_TEAM_NAME') or str(row['CONTESTANTHOME_OPTAUUID'])[:8]
                a_name = row.get('AWAY_TEAM_NAME') or str(row['CONTESTANTAWAY_OPTAUUID'])[:8]

                team_rows.append({
                    'TEAM': h_name,
                    'GOALS': pd.to_numeric(row.get('HOME_GOALS'), errors='coerce') or 0,
                    'SHOTS': pd.to_numeric(row.get('HOME_SHOTS'), errors='coerce') or 0,
                    'SHOTS_ON_TARGET': pd.to_numeric(row.get('HOME_SHOTS_ON_TARGET'), errors='coerce') or 0,
                    'XG': pd.to_numeric(row.get('HOME_XG'), errors='coerce') or 0.0,
                    'CORNERS': pd.to_numeric(row.get('HOME_CORNERS'), errors='coerce') or 0,
                    'FOULS': pd.to_numeric(row.get('HOME_FOULS'), errors='coerce') or 0,
                    'TACKLES': pd.to_numeric(row.get('HOME_TACKLES'), errors='coerce') or 0,
                    'SAVES': pd.to_numeric(row.get('HOME_SAVES'), errors='coerce') or 0
                })
                team_rows.append({
                    'TEAM': a_name,
                    'GOALS': pd.to_numeric(row.get('AWAY_GOALS'), errors='coerce') or 0,
                    'SHOTS': pd.to_numeric(row.get('AWAY_SHOTS'), errors='coerce') or 0,
                    'SHOTS_ON_TARGET': pd.to_numeric(row.get('AWAY_SHOTS_ON_TARGET'), errors='coerce') or 0,
                    'XG': pd.to_numeric(row.get('AWAY_XG'), errors='coerce') or 0.0,
                    'CORNERS': pd.to_numeric(row.get('AWAY_CORNERS'), errors='coerce') or 0,
                    'FOULS': pd.to_numeric(row.get('AWAY_FOULS'), errors='coerce') or 0,
                    'TACKLES': pd.to_numeric(row.get('AWAY_TACKLES'), errors='coerce') or 0,
                    'SAVES': pd.to_numeric(row.get('AWAY_SAVES'), errors='coerce') or 0
                })

            df_teams = pd.DataFrame(team_rows)
            if df_teams.empty:
                st.warning("Ikke nok data til at generere tabellen.")
                return

            agg_df = df_teams.groupby('TEAM').sum(numeric_only=True).reset_index()
            match_counts = df_teams.groupby('TEAM').size().reset_index(name='MATCHES')
            agg_df = pd.merge(agg_df, match_counts, on='TEAM')

            # --- TOP SEKTION: CAPTION ØVERST ---
            st.caption("1. Division — Over- og Underpræstation samt Sammenhænge")

            # --- OPRETTELSE AF TABS ---
            tab1, tab2 = st.tabs(["Baseline Oversigt", "Scatterplot"])

            HIF_RED = '#df003b'

            # --- TAB 1: BASELINE VISNING ---
            with tab1:
                metric_labels_tab1 = {
                    "Mål vs. Skud-baseline (Faktiske mål minus forventede ud fra skudvolumen)": "GOALS_VS_BASELINE",
                    "xG vs. Faktiske Mål (Afslutningskvalitet)": "XG_VS_GOALS",
                    "Skud på mål (Total)": "SHOTS_ON_TARGET",
                    "Hjørnespark": "CORNERS",
                    "Tacklinger": "TACKLES",
                    "Frispark": "FOULS",
                    "Redninger": "SAVES"
                }

                col_dropdown1, col_btn1 = st.columns([1.5, 0.5])
                with col_dropdown1:
                    selected_label1 = st.selectbox("Vælg parameter (baseline):", list(metric_labels_tab1.keys()), label_visibility="collapsed", key="baseline_dropdown")
                
                with col_btn1:
                    with st.popover("Data", use_container_width=True, key="popover_baseline_data"):
                        metric_key1_pop = metric_labels_tab1[selected_label1]
                        df_b_pop = agg_df.copy()

                        if metric_key1_pop == "GOALS_VS_BASELINE":
                            tot_g = df_b_pop['GOALS'].sum()
                            tot_s = df_b_pop['SHOTS'].sum()
                            conv = tot_g / tot_s if tot_s > 0 else 0.1
                            df_b_pop['BASELINE_VAL'] = df_b_pop['SHOTS'] * conv
                            df_b_pop['VAL'] = df_b_pop['GOALS'] - df_b_pop['BASELINE_VAL']
                            val_col_name = "Diff"
                        elif metric_key1_pop == "XG_VS_GOALS":
                            df_b_pop['VAL'] = df_b_pop['GOALS'] - df_b_pop['XG']
                            val_col_name = "Diff"
                        else:
                            avg_val = df_b_pop[metric_key1_pop].sum() / df_b_pop['MATCHES'].sum()
                            df_b_pop['BASELINE_VAL'] = df_b_pop['MATCHES'] * avg_val
                            df_b_pop['VAL'] = df_b_pop[metric_key1_pop] - df_b_pop['BASELINE_VAL']
                            val_col_name = "Diff"

                        df_table1 = df_b_pop[['TEAM', 'VAL', 'MATCHES']].copy()
                        df_table1.columns = ['Hold', val_col_name, 'Kampe']
                        df_table1[val_col_name] = df_table1[val_col_name].map('{:.2f}'.format)
                        
                        st.markdown("""
                            <style>
                                thead tr th:first-child { display:none; }
                                tbody tr th { display:none; }
                                table tr td:nth-child(2) { text-align: left !important; }
                                table tr td:nth-child(3), table tr td:nth-child(4) { text-align: center !important; }
                                table tr th:nth-child(3), table tr th:nth-child(4) { text-align: center !important; }
                                table { width: 100%; border-collapse: collapse; font-size: 12px; }
                                
                                table tr:has(td div:contains("Hvidovre")),
                                table tr:has(td span:contains("Hvidovre")),
                                table tr:has(td:contains("Hvidovre")) {
                                    background-color: #df003b !important;
                                }
                                table tr:has(td div:contains("Hvidovre")) td,
                                table tr:has(td span:contains("Hvidovre")) td,
                                table tr:has(td:contains("Hvidovre")) td {
                                    background-color: #df003b !important;
                                    color: white !important;
                                    font-weight: bold;
                                }
                                table tr:has(td div:contains("Hvidovre")) td *,
                                table tr:has(td span:contains("Hvidovre")) td *,
                                table tr:has(td:contains("Hvidovre")) td * {
                                    color: white !important;
                                }
                            </style>
                        """, unsafe_allow_html=True)
                        st.table(df_table1)

                metric_key1 = metric_labels_tab1[selected_label1]
                df_b = agg_df.copy()

                if metric_key1 == "GOALS_VS_BASELINE":
                    total_league_goals = df_b['GOALS'].sum()
                    total_league_shots = df_b['SHOTS'].sum()
                    league_conversion = total_league_goals / total_league_shots if total_league_shots > 0 else 0.1
                    
                    df_b['BASELINE_VAL'] = df_b['SHOTS'] * league_conversion
                    df_b['DIFF'] = df_b['GOALS'] - df_b['BASELINE_VAL']
                    chart_title = "Mål over eller under en skud-volumen baseline"
                    xaxis_title = "mål vs. skud-volumen baseline"

                elif metric_key1 == "XG_VS_GOALS":
                    df_b['DIFF'] = df_b['GOALS'] - df_b['XG']
                    chart_title = "Faktiske mål minus xG (Over/underpræstation på afslutninger)"
                    xaxis_title = "mål minus xG"

                else:
                    league_avg_per_match = df_b[metric_key1].sum() / df_b['MATCHES'].sum()
                    df_b['BASELINE_VAL'] = df_b['MATCHES'] * league_avg_per_match
                    df_b['DIFF'] = df_b[metric_key1] - df_b['BASELINE_VAL']
                    chart_title = f"{selected_label1} vs. Liga-gennemsnit"
                    xaxis_title = "forskel i forhold til gennemsnit"

                df_b = df_b.sort_values(by='DIFF', ascending=True)
                df_b['COLOR_TEAM'] = df_b['TEAM'].apply(lambda x: HIF_RED if str(x).strip().lower() == 'hvidovre' else 'gray')

                fig1 = px.bar(
                    df_b,
                    x='DIFF',
                    y='TEAM',
                    orientation='h',
                    title=chart_title,
                    text_auto='.2f',
                    custom_data=['TEAM', 'DIFF', 'MATCHES']
                )

                fig1.update_traces(
                    marker_color=df_b['COLOR_TEAM'],
                    textfont=dict(size=12, color='white'),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Præstation: %{x:.2f}<br>"
                        "Kampe spillet: %{customdata[2]}"
                        "<extra></extra>"
                    )
                )

                fig1.update_layout(
                    xaxis_title=xaxis_title,
                    yaxis_title="",
                    showlegend=False,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    title_font=dict(size=18, color='white'),
                    height=600,
                    margin=dict(t=60, b=40, l=40, r=40)
                )
                
                fig1.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333333', zerolinecolor='#555555')
                fig1.update_yaxes(showgrid=False)

                st.plotly_chart(fig1, use_container_width=True)

            # --- TAB 2: SCATTERPLOT VISNING ---
            with tab2:
                metric_labels_tab2 = {
                    "Skud vs. Mål": {"x": "SHOTS", "y": "GOALS"},
                    "xG vs. Mål": {"x": "XG", "y": "GOALS"},
                    "Skud på mål vs. Mål": {"x": "SHOTS_ON_TARGET", "y": "GOALS"},
                    "Hjørnespark vs. Mål": {"x": "CORNERS", "y": "GOALS"},
                    "Tacklinger vs. Mål": {"x": "TACKLES", "y": "GOALS"}
                }

                col_dropdown2, col_btn2 = st.columns([1.5, 0.5])
                with col_dropdown2:
                    selected_label2 = st.selectbox("Vælg analyse (scatter):", list(metric_labels_tab2.keys()), label_visibility="collapsed", key="scatter_dropdown")
                
                with col_btn2:
                    with st.popover("Data", use_container_width=True, key="popover_scatter_data"):
                        mapping = metric_labels_tab2[selected_label2]
                        x_col, y_col = mapping["x"], mapping["y"]
                        df_s_pop = agg_df.copy()
                        df_s_pop[x_col] = pd.to_numeric(df_s_pop[x_col], errors='coerce').fillna(0)
                        df_s_pop[y_col] = pd.to_numeric(df_s_pop[y_col], errors='coerce').fillna(0)

                        df_table = df_s_pop[['TEAM', x_col, y_col]].copy()
                        df_table.columns = ['Hold', x_col, y_col]
                        df_table[x_col] = df_table[x_col].map('{:.1f}'.format)
                        df_table[y_col] = df_table[y_col].map('{:.2f}'.format)
                        
                        st.markdown("""
                            <style>
                                thead tr th:first-child { display:none; }
                                tbody tr th { display:none; }
                                table tr td:nth-child(2) { text-align: left !important; }
                                table tr td:nth-child(3), table tr td:nth-child(4) { text-align: center !important; }
                                table tr th:nth-child(3), table tr th:nth-child(4) { text-align: center !important; }
                                table { width: 100%; border-collapse: collapse; font-size: 12px; }
                                
                                table tr:has(td div:contains("Hvidovre")),
                                table tr:has(td span:contains("Hvidovre")),
                                table tr:has(td:contains("Hvidovre")) {
                                    background-color: #df003b !important;
                                }
                                table tr:has(td div:contains("Hvidovre")) td,
                                table tr:has(td span:contains("Hvidovre")) td,
                                table tr:has(td:contains("Hvidovre")) td {
                                    background-color: #df003b !important;
                                    color: white !important;
                                    font-weight: bold;
                                }
                                table tr:has(td div:contains("Hvidovre")) td *,
                                table tr:has(td span:contains("Hvidovre")) td *,
                                table tr:has(td:contains("Hvidovre")) td * {
                                    color: white !important;
                                }
                            </style>
                        """, unsafe_allow_html=True)
                        st.table(df_table)

                # Generer selve scatterplottet i fuld størrelse
                mapping = metric_labels_tab2[selected_label2]
                x_col, y_col = mapping["x"], mapping["y"]

                df_s = agg_df.copy()
                df_s[x_col] = pd.to_numeric(df_s[x_col], errors='coerce').fillna(0)
                df_s[y_col] = pd.to_numeric(df_s[y_col], errors='coerce').fillna(0)

                fig2 = go.Figure()
                
                avg_x = df_s[x_col].mean()
                avg_y = df_s[y_col].mean()

                for _, row in df_s.iterrows():
                    team_name = row['TEAM']
                    is_hif = (str(team_name).strip().lower() == "hvidovre")
                    
                    fig2.add_trace(go.Scatter(
                        x=[row[x_col]], y=[row[y_col]],
                        mode='markers+text',
                        text=[team_name], 
                        textposition="top center",
                        textfont=dict(size=13, color='white', weight='bold' if is_hif else 'normal'),
                        marker=dict(
                            size=25 if is_hif else 18, 
                            color=HIF_RED if is_hif else 'gray',
                            line=dict(width=2, color='white')
                        ),
                        hovertemplate=f"<b>{team_name}</b><br>Total {x_col}: %{{x:.2f}}<br>Total {y_col}: %{{y:.2f}}<extra></extra>"
                    ))

                fig2.add_vline(x=avg_x, line_dash="dot", line_color="#777777")
                fig2.add_hline(y=avg_y, line_dash="dot", line_color="#777777")

                fig2.update_layout(
                    title=f"Sammenhæng mellem {x_col} og {y_col} (Totaler)",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    title_font=dict(size=18, color='white'),
                    xaxis_title=f"Total {x_col}",
                    yaxis_title=f"Total {y_col}",
                    height=600,
                    margin=dict(t=60, b=40, l=40, r=40),
                    showlegend=False
                )
                
                fig2.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333333')
                fig2.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333333')

                st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    except Exception as e:
        st.error(f"Fejl ved indlæsning af siden: {e}")
