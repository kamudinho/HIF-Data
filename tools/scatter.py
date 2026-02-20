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
        height=800,
        template="plotly_white",
        labels={
            "X_PER_GAME": f"{metric_type} For pr. kamp", 
            "Y_PER_GAME": f"{metric_type} Imod pr. kamp"
        },
        color_discrete_sequence=['#004d40'] # En solid fodbold-grøn eller klubfarve
    )

    # Vend Y-aksen så "få mål imod" er øverst (god præstation)
    fig.update_yaxes(autorange="reversed")

    # Tilpas prikkernes udseende og tekstens placering
    fig.update_traces(
        marker=dict(size=12, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')),
        textposition='top center'
    )

    # Gennemsnitslinjer
    avg_x = df_plot['X_PER_GAME'].mean()
    avg_y = df_plot['Y_PER_GAME'].mean()
    
    fig.add_hline(y=avg_y, line_dash="dot", line_color="grey", opacity=0.5, 
                  annotation_text="Gns. Imod", annotation_position="bottom right")
    fig.add_vline(x=avg_x, line_dash="dot", line_color="grey", opacity=0.5,
                  annotation_text="Gns. For", annotation_position="top left")
    
    return fig

def vis_side(df_scatter):
    st.write("### 📊 Hold Performance Scatterplot")
    
    c1, c2 = st.columns(2)
    with c1:
        leagues = sorted(df_scatter['COMPETITIONNAME'].unique())
        valgt_league = st.selectbox("Vælg Turnering", leagues)
    with c2:
        metric_type = st.selectbox("Vælg Analyse", ["xG (Expected Goals)", "Mål & Afslutninger"])

    df_filtered = df_scatter[df_scatter['COMPETITIONNAME'] == valgt_league].copy()
    
    if metric_type == "xG (Expected Goals)":
        x_col, y_col = 'XGSHOT', 'XGSHOTAGAINST'
    else:
        x_col, y_col = 'GOALS', 'CONCEDEDGOALS'

    with st.spinner("Genererer analyse..."):
        fig = build_scatter_plot(df_filtered, x_col, y_col, metric_type)
        st.plotly_chart(fig, use_container_width=True)
