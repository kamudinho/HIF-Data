import streamlit as st
import plotly.express as px
import pandas as pd

@st.cache_resource
def build_scatter_plot(df_plot, x_col, y_col, metric_type):
    fig = px.scatter(
        df_plot, 
        x='X_PER_GAME', 
        y='Y_PER_GAME',
        hover_name='TEAMNAME',
        text='TEAMNAME', 
        height=700,
        template="plotly_white",
        labels={
            "X_PER_GAME": f"{metric_type} For pr. kamp", 
            "Y_PER_GAME": f"{metric_type} Imod pr. kamp"
        },
        color_discrete_sequence=['#df003b'] 
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_traces(
        marker=dict(size=14, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')),
        textposition='top center'
    )

    avg_x = df_plot['X_PER_GAME'].mean()
    avg_y = df_plot['Y_PER_GAME'].mean()
    
    fig.add_hline(y=avg_y, line_dash="dot", line_color="grey", opacity=0.5)
    fig.add_vline(x=avg_x, line_dash="dot", line_color="grey", opacity=0.5)
    
    return fig

def vis_side(df_scatter):
    if df_scatter is None or df_scatter.empty:
        st.warning("Ingen scatter-data tilgængelige.")
        return

    # Hent den rå sæson-tekst (vi fjerner "=' " og " ' " fra filteret hvis nødvendigt)
    dp = st.session_state.get("data_package", {})
    # Vi bruger SEASONNAME direkte fra season_show hvis muligt, ellers renses filteret
    try:
        from data.season_show import SEASONNAME
        current_season = SEASONNAME
    except:
        current_season = dp.get("season_filter", "").replace("='", "").replace("'", "")

    st.write(f"### 📊 Hold Performance | {current_season}")
    
    df_s = df_scatter.copy()
    df_s.columns = [c.upper() for c in df_s.columns]
    
    # --- FEJLFIX: Dynamisk tjek af kolonnenavn ---
    s_col = None
    for possible_col in ['SEASONNAME', 'SEASON_NAME', 'SEASON']:
        if possible_col in df_s.columns:
            s_col = possible_col
            break
    
    if s_col:
        df_current = df_s[df_s[s_col] == current_season].copy()
    else:
        # Hvis kolonnen slet ikke findes, viser vi data som de er for at undgå crash
        df_current = df_s.copy()
    
    if df_current.empty:
        st.info(f"Ingen specifikke data for {current_season} i tabellen. Viser alt tilgængeligt.")
        df_current = df_s.copy()

    c1, c2 = st.columns(2)
    with c1:
        leagues = sorted(df_current['COMPETITIONNAME'].unique()) if 'COMPETITIONNAME' in df_current.columns else []
        valgt_league = st.selectbox("Vælg Turnering", leagues)
    with c2:
        metric_type = st.selectbox("Vælg Analyse", ["xG (Expected Goals)", "Mål & Afslutninger"])

    df_filtered = df_current[df_current['COMPETITIONNAME'] == valgt_league].copy()
    
    if not df_filtered.empty:
        x_col = 'XGSHOT' if metric_type == "xG (Expected Goals)" else 'GOALS'
        y_col = 'XGSHOTAGAINST' if metric_type == "xG (Expected Goals)" else 'CONCEDEDGOALS'
        
        # Beregn per kamp
        df_filtered['X_PER_GAME'] = df_filtered[x_col] / df_filtered['MATCHES']
        df_filtered['Y_PER_GAME'] = df_filtered[y_col] / df_filtered['MATCHES']

        fig = build_scatter_plot(df_filtered, x_col, y_col, metric_type)
        st.plotly_chart(fig, use_container_width=True)
