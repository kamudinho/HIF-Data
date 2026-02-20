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

    dp = st.session_state.get("data_package", {})
    
    # --- SIKKER SÆSON-HENTNING ---
    try:
        from data.season_show import SEASONNAME
        current_season = str(SEASONNAME).strip()
    except:
        current_season = str(dp.get("season_filter", "")).replace("='", "").replace("'", "").strip()

    st.write(f"### 📊 Hold Performance | {current_season}")
    
    df_s = df_scatter.copy()
    df_s.columns = [c.upper() for c in df_s.columns]
    
    # Find sæson-kolonnen
    s_col = next((c for c in ['SEASONNAME', 'SEASON_NAME', 'SEASON'] if c in df_s.columns), None)
    
    if s_col:
        # Tving kolonnen til tekst og fjern whitespace for at sikre match
        df_s[s_col] = df_s[s_col].astype(str).str.strip()
        df_current = df_s[df_s[s_col] == current_season].copy()
        
        # Hvis den stadig er tom, kan det skyldes at sæsonen i DB hedder noget andet
        if df_current.empty:
            available = df_s[s_col].unique()
            st.error(f"Kunne ikke finde data for '{current_season}'. Tilgængelige i DB: {available}")
            return
    else:
        st.error("Kunne ikke finde en sæson-kolonne i dataene.")
        return

    c1, c2 = st.columns(2)
    with c1:
        leagues = sorted(df_current['COMPETITIONNAME'].unique()) if 'COMPETITIONNAME' in df_current.columns else []
        valgt_league = st.selectbox("Vælg Turnering", leagues)
    with c2:
        metric_type = st.selectbox("Vælg Analyse", ["xG (Expected Goals)", "Mål & Afslutninger"])

    df_filtered = df_current[df_current['COMPETITIONNAME'] == valgt_league].copy()
    
    if not df_filtered.empty:
        # Beregn per kamp baseret på valgt metric
        if metric_type == "xG (Expected Goals)":
            x_col, y_col = 'XGSHOT', 'XGSHOTAGAINST'
        else:
            x_col, y_col = 'GOALS', 'CONCEDEDGOALS'
        
        df_filtered['X_PER_GAME'] = df_filtered[x_col] / df_filtered['MATCHES']
        df_filtered['Y_PER_GAME'] = df_filtered[y_col] / df_filtered['MATCHES']

        fig = build_scatter_plot(df_filtered, x_col, y_col, metric_type)
        st.plotly_chart(fig, use_container_width=True)
