import streamlit as st
import plotly.express as px
import pandas as pd
from data.data_load import get_team_colors

def build_scatter_plot(df_plot, metric_type):
    # Hent farverne fra din centrale konfiguration
    colors_dict = get_team_colors()
    
    fig = px.scatter(
        df_plot, 
        x='X_PER_GAME', 
        y='Y_PER_GAME',
        hover_name='TEAMNAME',
        text='TEAMNAME', 
        color='TEAMNAME', # Aktiverer farve-mapping
        color_discrete_map=colors_dict, # Mapper holdnavn til farve
        height=700,
        template="plotly_white",
        labels={
            "X_PER_GAME": f"{metric_type} For pr. kamp", 
            "Y_PER_GAME": f"{metric_type} Imod pr. kamp"
        }
    )

    # Vender Y-aksen (færre mål imod i toppen er godt)
    fig.update_yaxes(autorange="reversed")
    
    fig.update_traces(
        marker=dict(size=16, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')),
        textposition='top center'
    )

    # Gennemsnitslinjer
    avg_x = df_plot['X_PER_GAME'].mean()
    avg_y = df_plot['Y_PER_GAME'].mean()
    fig.add_hline(y=avg_y, line_dash="dot", line_color="grey", opacity=0.5)
    fig.add_vline(x=avg_x, line_dash="dot", line_color="grey", opacity=0.5)
    
    # Skjul legenden i siden (navnene står allerede ved prikkerne)
    fig.update_layout(showlegend=False)
    
    return fig

def vis_side(df_scatter):
    if df_scatter is None or df_scatter.empty:
        st.warning("Ingen scatter-data tilgængelige.")
        return

    # 1. Standardiser kolonner
    df_s = df_scatter.copy()
    df_s.columns = [c.upper() for c in df_s.columns]
    
    # 2. Hent sæson (fallback hvis import fejler)
    try:
        from data.season_show import SEASONNAME
        current_season = str(SEASONNAME).strip()
    except:
        current_season = "2025/2026"

    # 3. Filtrering
    s_col = next((c for c in df_s.columns if 'SEASON' in c), None)
    if not s_col:
        st.error("Kunne ikke finde sæson-kolonne.")
        return

    df_current = df_s[df_s[s_col].astype(str).str.strip() == current_season].copy()
    
    st.markdown('<div class="custom-header"><h3>SCATTERPLOTS</h3></div>', unsafe_allow_html=True)
    
    # 4. Dropdowns
    c1, c2 = st.columns(2)
    with c1:
        leagues = sorted(df_current['COMPETITIONNAME'].unique()) if 'COMPETITIONNAME' in df_current.columns else []
        valgt_league = st.selectbox("Vælg Turnering", leagues)
    with c2:
        metric_type = st.selectbox("Vælg Analyse", ["xG (Expected Goals)", "Mål & Afslutninger"])

    df_filtered = df_current[df_current['COMPETITIONNAME'] == valgt_league].copy()
    
    if not df_filtered.empty:
        # Vælg rå kolonner
        x_raw, y_raw = ('XGSHOT', 'XGSHOTAGAINST') if metric_type == "xG (Expected Goals)" else ('GOALS', 'CONCEDEDGOALS')
        
        # Beregn pr. kamp
        for col in [x_raw, y_raw, 'MATCHES']:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0)

        df_filtered['X_PER_GAME'] = df_filtered[x_raw] / df_filtered['MATCHES'].replace(0, 1)
        df_filtered['Y_PER_GAME'] = df_filtered[y_raw] / df_filtered['MATCHES'].replace(0, 1)

        # Vis graf
        fig = build_scatter_plot(df_filtered, metric_type)
        st.plotly_chart(fig, use_container_width=True)
