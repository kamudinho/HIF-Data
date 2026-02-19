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
        # Mulighed for at skifte mellem xG og faktiske mål
        metric_type = st.selectbox("Vælg Analyse", ["xG (Expected Goals)", "Mål & Afslutninger"])

    # Filtrér data baseret på liga
    df_filtered = df_scatter[df_scatter['COMPETITIONNAME'] == valgt_league].copy()
    
    # --- DYNAMISK MAPPING AF KOLONNER ---
    # Vi bruger de navne, som din fejlbesked bekræftede findes i dit dataframe
    if metric_type == "xG (Expected Goals)":
        x_col = 'XGSHOT'         # xG For
        y_col = 'XGSHOTAGAINST'  # xG Imod
    else:
        x_col = 'GOALS'          # Mål For
        y_col = 'CONCEDEDGOALS'  # Mål Imod (fundet i din liste)

    # Beregn gennemsnit pr. kamp (da tallene er Total-stats fra din query)
    df_filtered['X_PER_GAME'] = df_filtered[x_col] / df_filtered['MATCHES']
    df_filtered['Y_PER_GAME'] = df_filtered[y_col] / df_filtered['MATCHES']

    # --- PLOT OPSÆTNING ---
    fig = px.scatter(
        df_filtered, 
        x='X_PER_GAME', 
        y='Y_PER_GAME',
        hover_name='TEAMNAME',
        hover_data={'MATCHES': True, 'X_PER_GAME': ':.2f', 'Y_PER_GAME': ':.2f'},
        height=800,
        template="plotly_white",
        labels={
            "X_PER_GAME": f"{metric_type} For pr. kamp",
            "Y_PER_GAME": f"{metric_type} Imod pr. kamp"
        }
    )

    # Invertér Y-aksen (Færre mål/xG imod er bedre = skal være øverst)
    fig.update_yaxes(autorange="reversed")

    # --- TILFØJ LOGOER ---
    # Vi bruger imagedataurl fra din query
    for i, row in df_filtered.iterrows():
        if pd.notnull(row['IMAGEDATAURL']):
            fig.add_layout_image(
                dict(
                    source=row['IMAGEDATAURL'],
                    xref="x", yref="y",
                    x=row['X_PER_GAME'],
                    y=row['Y_PER_GAME'],
                    sizex=0.10, sizey=0.10, # Justeret størrelse til "per game" skala
                    xhalign="center", yhalign="middle",
                    layer="above"
                )
            )

    # Gør de originale prikker usynlige
    fig.update_traces(marker=dict(color='rgba(0,0,0,0)'))

    # Gennemsnitslinjer
    avg_x = df_filtered['X_PER_GAME'].mean()
    avg_y = df_filtered['Y_PER_GAME'].mean()
    fig.add_hline(y=avg_y, line_dash="dot", line_color="grey", opacity=0.5)
    fig.add_vline(x=avg_x, line_dash="dot", line_color="grey", opacity=0.5)

    st.plotly_chart(fig, use_container_width=True)
