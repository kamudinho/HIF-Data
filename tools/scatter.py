import streamlit as st
import plotly.express as px
import pandas as pd

# Skift til cache_data eller fjern den helt under debugging
@st.cache_data
def build_scatter_plot(df_plot, metric_type):
    # Vi bruger de præcise kolonnenavne vi lige har lavet
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

    # Vender Y-aksen så færre mål imod er i TOPPEN (godt)
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

    # 1. Standardiser kolonner med det samme
    df_s = df_scatter.copy()
    df_s.columns = [c.upper() for c in df_s.columns]
    
    # 2. Hent sæson-konfiguration
    try:
        from data.season_show import SEASONNAME
        current_season = str(SEASONNAME).strip()
    except:
        current_season = "2025/2026"

    # 3. Find sæson-kolonne
    s_col = next((c for c in df_s.columns if 'SEASON' in c), None)
    
    if not s_col:
        st.error("Kunne ikke finde sæson-kolonne.")
        return

    df_s[s_col] = df_s[s_col].astype(str).str.strip()
    df_current = df_s[df_s[s_col] == current_season].copy()
    
    if df_current.empty:
        st.warning(f"Ingen data for {current_season}")
        return

    st.markdown('<div class="custom-header"><h3>SCATTERPLOTS</h3></div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        leagues = sorted(df_current['COMPETITIONNAME'].unique()) if 'COMPETITIONNAME' in df_current.columns else []
        valgt_league = st.selectbox("Vælg Turnering", leagues)
    with c2:
        metric_type = st.selectbox("Vælg Analyse", ["xG (Expected Goals)", "Mål & Afslutninger"])

    df_filtered = df_current[df_current['COMPETITIONNAME'] == valgt_league].copy()
    
    if not df_filtered.empty:
        # Vælg rå kolonner baseret på analyse
        if metric_type == "xG (Expected Goals)":
            x_raw, y_raw = 'XGSHOT', 'XGSHOTAGAINST'
        else:
            x_raw, y_raw = 'GOALS', 'CONCEDEDGOALS'
        
        # SIKKERHED: Tjek om kolonnerne findes før beregning
        needed = [x_raw, y_raw, 'MATCHES']
        missing = [c for c in needed if c not in df_filtered.columns]
        
        if missing:
            st.error(f"Mangler kolonner i data: {missing}")
            return

        # Konverter og beregn
        for col in needed:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0)

        df_filtered['X_PER_GAME'] = df_filtered[x_raw] / df_filtered['MATCHES'].replace(0, 1)
        df_filtered['Y_PER_GAME'] = df_filtered[y_raw] / df_filtered['MATCHES'].replace(0, 1)

        # Send data til plot-funktion
        fig = build_scatter_plot(df_filtered, metric_type)
        st.plotly_chart(fig, use_container_width=True)
