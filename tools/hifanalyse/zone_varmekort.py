import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

SEASONNAME = "2025/2026"
TEAM_WYID = 7490

def vis_side():
    st.title("🗺️ Varmekort (Zoner)")
    st.markdown(f"**Sæson:** {SEASONNAME} | **Hold ID:** {TEAM_WYID}")

    st.markdown("Visualisering af Hvidovre IFs aktioner opdelt efter banens geografiske zoner.")

    # Eksempel på zone-data (10 baneregioner fra forsvar til angreb)
    zoner = [
        "Defensiv Venstre", "Defensiv Central", "Defensiv Højre",
        "Midtbane Venstre", "Central Midtbane", "Midtbane Højre",
        "Offensiv Venstre", "Offensiv Central", "Offensiv Højre", "Modstanderens Felt"
    ]

    # Simulerer aktivitetsfrekvens (f.eks. antal afleveringer eller genvindinger)
    @st.cache_data
    def hent_zone_data():
        np.random.seed(100)
        vaerdier = np.random.randint(40, 250, size=len(zoner))
        df = pd.DataFrame({
            "Zone": zoner,
            "Aktioner": vaerdier,
            "X_pos": [1, 1, 1, 2, 2, 2, 3, 3, 3, 4],
            "Y_pos": [1, 2, 3, 1, 2, 3, 1, 2, 3, 2]
        })
        return df

    df_zoner = hent_zone_data()

    # Vis som et heatmap / scatter plot med store markører fordelt på banen
    fig = px.scatter(
        df_zoner, x="X_pos", y="Y_pos", 
        size="Aktioner", color="Aktioner",
        hover_name="Zone",
        size_max=60,
        color_continuous_scale="Reds",
        title="Aktionsintensitet fordelt på banenzoner"
    )
    
    # Tilpas layoutet så det minder mere om en bane
    fig.update_layout(
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=500
    )

    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("Top Zoner")
        top_zoner = df_zoner.sort_values(by="Aktioner", ascending=False).head(5)
        st.dataframe(top_zoner[["Zone", "Aktioner"]], use_container_width=True)
