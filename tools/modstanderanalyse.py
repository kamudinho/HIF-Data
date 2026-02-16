import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import seaborn as sns
import matplotlib.pyplot as plt

def vis_side():
    st.markdown("### 🛡️ Taktisk Modstanderanalyse")
    st.markdown("Analyse af offensive mønstre, afslutninger og skud imod.")

    try:
        # 1. Indlæs data
        df = pd.read_csv("data/team_matches.csv")
        
        st.sidebar.header("Analyse Indstillinger")
        valgt_kamp = st.sidebar.selectbox("Vælg Kamp", df['MATCHLABEL'].unique())
        kamp_data = df[df['MATCHLABEL'] == valgt_kamp]
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Aktioner", len(kamp_data))
        col2.metric("Egne Skud", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']))
        col3.metric("Skud imod", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']))

        # 2. Vælg type af analyse
        vis_type = st.radio(
            "Vælg heatmap kategori:", 
            ["Pasninger (med pile)", "Egne Skud", "Skud imod"], 
            horizontal=True
        )

        # 3. Opsætning af bane
        pitch = VerticalPitch(
            pitch_type='wyscout', 
            pitch_color='white', 
            line_color='#555555',
            linewidth=2
        )
        fig, ax = pitch.draw(figsize=(6, 8))
        fig.patch.set_facecolor('white')

        # 4. Logik for de tre typer
        if vis_type == "Pasninger (med pile)":
            data = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            cmap = 'Reds'
            label = "Pasningsintensitet"
            
            # Tegn heatmap
            if not data.empty:
                sns.kdeplot(
                    x=data['LOCATIONY'], y=data['LOCATIONX'],
                    fill=True, alpha=.5, n_levels=15, cmap=cmap,
                    ax=ax, clip=((0, 100), (0, 100)), linewidths=0
                )
                # Tegn pile (Bemærk: Vi bruger LOCATIONX/Y som start. 
                # Hvis du har slut-koordinater i din CSV, skal de indsættes her)
                # Da vi kun har ét punkt i din nuværende CSV, tegner vi korte pile 
                # for at vise position. Hvis du har END_X/Y, så skift 5-tallene ud.
                pitch.arrows(data.LOCATIONX, data.LOCATIONY, 
                             data.LOCATIONX + 2, data.LOCATIONY, 
                             width=2, headwidth=10, headlength=10, 
                             color='#3498db', ax=ax, alpha=0.4, label='Pasning (retning)')

        elif vis_type == "Egne Skud":
            data = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']
            cmap = 'YlOrBr'
            if not data.empty:
                sns.kdeplot(
                    x=data['LOCATIONY'], y=data['LOCATIONX'],
                    fill=True, alpha=.7, n_levels=15, cmap=cmap,
                    ax=ax, clip=((0, 100), (0, 100)), linewidths=0
                )
                pitch.scatter(data.LOCATIONX, data.LOCATIONY, color='red', 
                              edgecolors='black', s=150, ax=ax, label='Skudposition')

        elif vis_type == "Skud imod":
            data = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']
            cmap = 'Purples'
            if not data.empty:
                sns.kdeplot(
                    x=data['LOCATIONY'], y=data['LOCATIONX'],
                    fill=True, alpha=.7, n_levels=15, cmap=cmap,
                    ax=ax, clip=((0, 100), (0, 100)), linewidths=0
                )
                pitch.scatter(data.LOCATIONX, data.LOCATIONY, color='purple', 
                              edgecolors='white', s=150, ax=ax, label='Modstander skud')

        # Centrer banen
        c1, c2, c3 = st.columns([1, 3, 1])
        with c2:
            st.pyplot(fig)

    except Exception as e:
        st.error(f"Fejl: {e}")

if __name__ == "__main__":
    vis_side()
