import streamlit as st
import plotly.express as px
import pandas as pd
from data.data_load import get_team_colors # Importér farverne

@st.cache_data
def build_scatter_plot(df_plot, metric_type):
    colors_dict = get_team_colors()
    
    # Lav plottet med farve-mapping
    fig = px.scatter(
        df_plot, 
        x='X_PER_GAME', 
        y='Y_PER_GAME',
        hover_name='TEAMNAME',
        text='TEAMNAME', 
        color='TEAMNAME', # Vi fortæller Plotly at farven afhænger af holdet
        color_discrete_map=colors_dict, # Her mapper vi navnene til koderne
        height=700,
        template="plotly_white",
        labels={
            "X_PER_GAME": f"{metric_type} For pr. kamp", 
            "Y_PER_GAME": f"{metric_type} Imod pr. kamp",
            "TEAMNAME": "Hold"
        }
    )

    # ... resten af din styling (autorange="reversed", hline, vline osv.) ...
    fig.update_yaxes(autorange="reversed")
    fig.update_traces(
        marker=dict(size=16, opacity=0.9, line=dict(width=1.5, color='white')),
        textposition='top center'
    )
    
    # Fjern farve-legenden i siden for at give mere plads til selve grafen
    fig.update_layout(showlegend=False)
    
    return fig
