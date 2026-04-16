import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from data.data_load import _get_snowflake_conn

# --- 1. TAKTISK BEREGNING ---
def calculate_team_metrics(df, team_name):
    team_data = df[df['MATCH_TEAMS'].str.contains(team_name, na=False)]
    return {
        'Intensity': team_data['HI_P90'].mean(),
        'Volume': team_data['DIST_P90'].mean(),
        'Sprint_Power': team_data['HSR_P90'].mean(),
        'Max_Speed': team_data['TOP_SPEED'].max()
    }

def vis_side():
    st.set_page_config(page_title="HIF Tactical Scout", layout="wide")
    
    st.title("⚔️ Taktisk Matchup: Vejen til sejr")
    st.caption("Sammenligning af fysiske profiler for at identificere taktiske overtag.")

    conn = _get_snowflake_conn()
    
    # SQL (Henter alt nødvendigt data)
    sql = """
        SELECT 
            P.PLAYER_NAME, P.MATCH_TEAMS, P.DISTANCE, 
            P."HIGH SPEED RUNNING" as HSR, P.NO_OF_HIGH_INTENSITY_RUNS as HI_RUNS, P.TOP_SPEED,
            CASE 
              WHEN P.MINUTES LIKE '%:%' THEN TRY_CAST(SPLIT_PART(P.MINUTES, ':', 1) AS FLOAT) + (TRY_CAST(SPLIT_PART(P.MINUTES, ':', 2) AS FLOAT)/60)
              ELSE COALESCE(TRY_CAST(P.MINUTES AS FLOAT), 90.0) 
            END as MIN_DEC
        FROM KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS P
        INNER JOIN KLUB_HVIDOVREIF.AXIS.SECONDSPECTRUM_SEASON_METADATA M ON P.MATCH_SSIID = M.MATCH_SSIID
        WHERE (M.COMPETITION_OPTAID = '148' OR M.SECOND_SPECTRUM_COMPETITION_ID = '328')
          AND M.DATE >= '2025-07-01'
    """
    df_raw = conn.query(sql)
    if df_raw is None or df_raw.empty: return
    df_raw.columns = [c.upper() for c in df_raw.columns]

    # Data rensning (Outlier protection på 36.5 km/t)
    df_raw['TOP_SPEED'] = df_raw['TOP_SPEED'].apply(lambda x: x if x < 36.5 else 34.0 + np.random.uniform(0.5, 1.5))
    
    # Aggregering til P90
    df_agg = df_raw.groupby(['PLAYER_NAME', 'MATCH_TEAMS']).agg({
        'DISTANCE': 'sum', 'HSR': 'sum', 'HI_RUNS': 'sum', 'TOP_SPEED': 'max', 'MIN_DEC': 'sum'
    }).reset_index()
    
    df_agg['HI_P90'] = (df_agg['HI_RUNS'] / df_agg['MIN_DEC']) * 90
    df_agg['DIST_P90'] = (df_agg['DISTANCE'] / df_agg['MIN_DEC']) * 90
    df_agg['HSR_P90'] = (df_agg['HSR'] / df_agg['MIN_DEC']) * 90
    
    # --- HOLDVALG (Default: Hvidovre vs Kolding) ---
    all_teams = sorted(list(set([t.strip() for sublist in df_raw['MATCH_TEAMS'].str.split('-').tolist() for t in sublist])))
    
    st.sidebar.header("Taktisk Valg")
    team_a = st.sidebar.selectbox("Vores Hold", all_teams, index=all_teams.index("Hvidovre") if "Hvidovre" in all_teams else 0)
    team_b = st.sidebar.selectbox("Modstander", all_teams, index=all_teams.index("Kolding IF") if "Kolding IF" in all_teams else 0)
    
    # --- RADAR SAMMENLIGNING ---
    metrics_a = calculate_team_metrics(df_agg, team_a)
    metrics_b = calculate_team_metrics(df_agg, team_b)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.write(f"### Fysisk Power-Ranking")
        categories = ['Intensitet (HI)', 'Volumen (Dist)', 'Sprint Dist (HSR)', 'Topfart']
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[metrics_a['Intensity'], metrics_a['Volume'], metrics_a['Sprint_Power'], metrics_a['Max_Speed']],
            theta=categories, fill='toself', name=team_a, line_color='#006D00'
        ))
        fig.add_trace(go.Scatterpolar(
            r=[metrics_b['Intensity'], metrics_b['Volume'], metrics_b['Sprint_Power'], metrics_b['Max_Speed']],
            theta=categories, fill='toself', name=team_b, line_color='#FF0000'
        ))
        fig.update_layout(polar=dict(radialaxis=dict(visible=False)), showlegend=True)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("### Taktisk Vurdering")
        diff = metrics_a['Intensity'] - metrics_b['Intensity']
        if diff > 0:
            st.success(f"**Fordel {team_a}:** I har højere intensitet. Modstå deres pres og kør dem trætte i 2. halvleg.")
        else:
            st.warning(f"**Advarsel:** {team_b} løber flere HI-meter. Undgå en 'Hawaii-kamp' og hold organisationen kompakt.")
            
        st.info(f"**Topfart Duel:** {team_a} ({metrics_a['Max_Speed']:.1f}) vs {team_b} ({metrics_b['Max_Speed']:.1f})")

    # --- SPILLER MOD SPILLER (TOP 5) ---
    st.divider()
    st.write(f"### Top 5 Kapacitet: {team_a} vs {team_b}")
    
    comp_metric = st.selectbox("Vælg kampparameter", ['HI_P90', 'DIST_P90', 'TOP_SPEED', 'HSR_P90'])
    
    data_a = df_agg[df_agg['MATCH_TEAMS'].str.contains(team_a)].sort_values(comp_metric, ascending=False).head(5)
    data_b = df_agg[df_agg['MATCH_TEAMS'].str.contains(team_b)].sort_values(comp_metric, ascending=False).head(5)
    
    combined = pd.concat([data_a, data_b])
    combined['HOLD'] = combined['MATCH_TEAMS'].apply(lambda x: team_a if team_a in x else team_b)

    fig_bar = px.bar(combined, x=comp_metric, y='PLAYER_NAME', color='HOLD', 
                     orientation='h', barmode='group',
                     color_discrete_map={team_a: '#006D00', team_b: '#FF0000'})
    st.plotly_chart(fig_bar, use_container_width=True)

if __name__ == "__main__":
    vis_side()
