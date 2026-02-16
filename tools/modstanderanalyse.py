import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import seaborn as sns
import matplotlib.pyplot as plt

def vis_side():
    st.title("🛡️ Taktisk Modstanderanalyse")
    st.markdown("Her analyseres de 26.000 vigtigste offensive aktioner fra sæsonen.")

    # 1. Indlæs data
    try:
        df = pd.read_csv("team_matches.csv")
        
        # 2. Sidebar filtre
        st.sidebar.header("Analyse Indstillinger")
        valgt_kamp = st.sidebar.selectbox("Vælg Kamp/Modstander", df['MATCHLABEL'].unique())
        
        # Filtrer data
        kamp_data = df[df['MATCHLABEL'] == valgt_kamp]
        
        # 3. Layout med kolonner til metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Offensive Aktions", len(kamp_data))
        with col2:
            st.metric("Egne Skud", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']))
        with col3:
            st.metric("Skud imod", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']))

        # 4. Visualisering af banen
        st.subheader(f"Taktisk mønster: {valgt_kamp}")
        
        # Vælg visualiseringstype
        vis_type = st.radio("Vælg visning:", ["Heatmap (Tendenser)", "Scatter (Enkelte aktioner)"], horizontal=True)

        pitch = Pitch(pitch_type='wyscout', pitch_color='#22312b', line_color='#c7d5cc')
        fig, ax = pitch.draw(figsize=(10, 7))

        if vis_type == "Heatmap (Tendenser)":
            # Lav heatmap over offensive pasninger (LOCATIONX > 60)
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            if not passes.empty:
                kde = sns.kdeplot(
                    x=passes['LOCATIONX'],
                    y=passes['LOCATIONY'],
                    fill=True,
                    shade_lowest=False,
                    alpha=.5,
                    n_levels=10,
                    cmap='magma',
                    ax=ax
                )
            st.info("Heatmap viser, hvor modstanderen oftest har bolden på jeres banehalvdel.")

        else:
            # Scatter plot af skud og pasninger
            # Pasninger
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            pitch.scatter(passes['LOCATIONX'], passes['LOCATIONY'], ax=ax, color='cyan', alpha=0.3, s=20, label='Pasning')
            # Skud
            shots = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']
            pitch.scatter(shots['LOCATIONX'], shots['LOCATIONY'], ax=ax, color='red', s=100, edgecolors='white', label='Skud')
            ax.legend(facecolor='#22312b', edgecolor='None', labelcolor='white', loc='upper left')

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Kunne ikke indlæse data: {e}")
        st.info("Sørg for at 'team_matches.csv' er uploadet til GitHub.")

# Kør funktionen hvis filen køres direkte
if __name__ == "__main__":
    vis_side()
