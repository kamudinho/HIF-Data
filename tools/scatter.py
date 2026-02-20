import streamlit as st
import plotly.express as px
import pandas as pd

@st.cache_resource
def build_scatter_plot(df_filtered, x_col, y_col, metric_type):
    """Denne funktion er optimeret til at bruge standard Plotly markers."""
    
    # Beregn per kamp
    df_plot = df_filtered.copy()
    df_plot['X_PER_GAME'] = df_plot[x_col] / df_plot['MATCHES']
    df_plot['Y_PER_GAME'] = df_plot[y_col] / df_plot['MATCHES']

    fig = px.scatter(
        df_plot, 
        x='X_PER_GAME', 
        y='Y_PER_GAME',
        hover_name='TEAMNAME',
        text='TEAMNAME', # Tilføjer holdnavn ved prikken
        height=700,
        template="plotly_white",
        labels={
            "X_PER_GAME": f"{metric_type} For pr. kamp", 
            "Y_PER_GAME": f"{metric_type} Imod pr. kamp"
        },
        color_discrete_sequence=['#df003b'] # HIF rød eller en solid kontrastfarve
    )

    # Vend Y-aksen så "få mål imod" er øverst (god præstation)
    fig.update_yaxes(autorange="reversed")

    # Tilpas prikkernes udseende og tekstens placering
    fig.update_traces(
        marker=dict(size=14, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')),
        textposition='top center'
    )

    # Gennemsnitslinjer
    avg_x = df_plot['X_PER_GAME'].mean()
    avg_y = df_plot['Y_PER_GAME'].mean()
    
    fig.add_hline(y=avg_y, line_dash="dot", line_color="grey", opacity=0.5, 
                  annotation_text="Gns. Imod", annotation_position="bottom right")
    fig.add_vline(x=avg_x, line_dash="dot", line_color="grey", opacity=0.5,
                  annotation_text="Gns. For", annotation_position="top left")
    
    # Tilføj kvadrant-forklaringer
    fig.add_annotation(x=df_plot['X_PER_GAME'].max(), y=df_plot['Y_PER_GAME'].min(), text="Stærk Offensiv / Stærk Defensiv", showarrow=False, font=dict(color="green"))
    
    return fig

def vis_side(df_scatter):
    # Hent sæson-filteret fra session_state (sat i data_load.py)
    current_season = st.session_state["data_package"]["season_filter"]
    
    st.write(f"### 📊 Hold Performance | {current_season}")
    
    # 1. Filtrer straks på nuværende sæson
    # Vi antager kolonnen hedder 'SEASONNAME' (juster hvis Snowflake bruger andet navn)
    season_col = 'SEASONNAME' if 'SEASONNAME' in df_scatter.columns else 'SEASON'
    df_current = df_scatter[df_scatter[season_col] == current_season].copy()
    
    if df_current.empty:
        st.warning(f"Ingen data fundet for sæsonen {current_season}")
        return

    c1, c2 = st.columns(2)
    with c1:
        leagues = sorted(df_current['COMPETITIONNAME'].unique())
        valgt_league = st.selectbox("Vælg Turnering", leagues)
    with c2:
        metric_type = st.selectbox("Vælg Analyse", ["xG (Expected Goals)", "Mål & Afslutninger"])

    # 2. Filtrer på den valgte liga (indenfor den nuværende sæson)
    df_filtered = df_current[df_current['COMPETITIONNAME'] == valgt_league].copy()
    
    if metric_type == "xG (Expected Goals)":
        x_col, y_col = 'XGSHOT', 'XGSHOTAGAINST'
    else:
        x_col, y_col = 'GOALS', 'CONCEDEDGOALS'

    with st.spinner("Genererer analyse..."):
        fig = build_scatter_plot(df_filtered, x_col, y_col, metric_type)
        st.plotly_chart(fig, use_container_width=True)
