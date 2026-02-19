import streamlit as st
import plotly.express as px
import pandas as pd

def vis_side(df_scatter):
    st.write("### 📊 Hold Performance Scatterplot")
    
    # --- FILTRE ---
    c1, c2 = st.columns(2)
    with c1:
        leagues = sorted(df_scatter['COMPETITIONNAME'].unique())
        valgt_league = st.selectbox("Vælg Turnering", leagues)
    with c2:
        metric_type = st.selectbox("Vælg Analyse", ["xG (Expected Goals)", "Mål & Afslutninger"])

    df_filtered = df_scatter[df_scatter['COMPETITIONNAME'] == valgt_league].copy()
    
    # Mapping af kolonner (baseret på din Snowflake liste)
    if metric_type == "xG (Expected Goals)":
        x_col, y_col = 'XGSHOT', 'XGSHOTAGAINST'
    else:
        x_col, y_col = 'GOALS', 'CONCEDEDGOALS'

    # Beregn per kamp
    df_filtered['X_PER_GAME'] = df_filtered[x_col] / df_filtered['MATCHES']
    df_filtered['Y_PER_GAME'] = df_filtered[y_col] / df_filtered['MATCHES']

    # --- PLOT ---
    fig = px.scatter(
        df_filtered, 
        x='X_PER_GAME', 
        y='Y_PER_GAME',
        hover_name='TEAMNAME',
        height=800,
        template="plotly_white",
        labels={"X_PER_GAME": f"{metric_type} For pr. kamp", "Y_PER_GAME": f"{metric_type} Imod pr. kamp"}
    )

    fig.update_yaxes(autorange="reversed")

    # --- TILFØJ LOGOER (RETTET) ---
    for i, row in df_filtered.iterrows():
        if pd.notnull(row['IMAGEDATAURL']):
            fig.add_layout_image(
                dict(
                    source=row['IMAGEDATAURL'],
                    xref="x", yref="y",
                    x=row['X_PER_GAME'],
                    y=row['Y_PER_GAME'],
                    sizex=0.10, sizey=0.10,
                    xanchor="center", # RETTET FRA xhalign
                    yanchor="middle", # RETTET FRA yhalign
                    layer="above"
                )
            )

    fig.update_traces(marker=dict(color='rgba(0,0,0,0)'))

    # Gennemsnitslinjer
    avg_x = df_filtered['X_PER_GAME'].mean()
    avg_y = df_filtered['Y_PER_GAME'].mean()
    fig.add_hline(y=avg_y, line_dash="dot", line_color="grey", opacity=0.5)
    fig.add_vline(x=avg_x, line_dash="dot", line_color="grey", opacity=0.5)

    st.plotly_chart(fig, use_container_width=True)
