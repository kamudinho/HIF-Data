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
        # Her kan du tilføje de kolonner fra din tm.* som du vil sammenligne
        metric_type = st.selectbox("Vælg Analyse", ["xG vs xG imod", "Mål vs Mål imod"])

    # Filtrér data
    df_filtered = df_scatter[df_scatter['COMPETITIONNAME'] == valgt_league].copy()
    
    # Mapping af akser (Ret disse navne så de matcher dine tm.* kolonnenavne præcist)
    if metric_type == "xG vs xG imod":
        x_col, y_col = 'XG', 'XG_AGAINST' # Tjek om de hedder præcis dette i din tabel
    else:
        x_col, y_col = 'GOALS', 'GOALS_AGAINST'

    # --- PLOT OPSÆTNING ---
    fig = px.scatter(
        df_filtered, 
        x=x_col, 
        y=y_col,
        hover_name='TEAMNAME',
        text='TEAMNAME', # Viser navnet som backup
        height=800,
        template="plotly_white"
    )

    # Invertér Y-aksen (Færre mål imod = højere oppe)
    fig.update_yaxes(autorange="reversed")

    # --- TILFØJ LOGOER ---
    for i, row in df_filtered.iterrows():
        if pd.notnull(row['IMAGEDATAURL']):
            fig.add_layout_image(
                dict(
                    source=row['IMAGEDATAURL'],
                    xref="x", yref="y",
                    x=row[x_col],
                    y=row[y_col],
                    sizex=0.8, sizey=0.8, # Justér størrelse afhængig af aksens skala
                    xhalign="center", yhalign="middle",
                    layer="above"
                )
            )

    # Gør de blå prikker usynlige så kun logoet og teksten ses
    fig.update_traces(marker=dict(color='rgba(0,0,0,0)'), textposition='top center')

    # Gennemsnitslinjer for kvadrant-opdeling
    avg_x = df_filtered[x_col].mean()
    avg_y = df_filtered[y_col].mean()
    
    fig.add_hline(y=avg_y, line_dash="dot", line_color="grey", opacity=0.5)
    fig.add_vline(x=avg_x, line_dash="dot", line_color="grey", opacity=0.5)

    st.plotly_chart(fig, use_container_width=True)

    # Kvadrant guide
    st.caption("Øverst til højre: God offensiv & God defensiv | Nederst til venstre: Svag offensiv & Svag defensiv")
