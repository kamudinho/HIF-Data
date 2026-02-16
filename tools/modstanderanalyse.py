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
        df = pd.read_csv("data/team_matches.csv")
        
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

        # Ændret til hvid baggrund og grå/sorte linjer
        pitch = Pitch(pitch_type='wyscout', pitch_color='white', line_color='#555555')
        fig, ax = pitch.draw(figsize=(10, 7))
        
        # Sørg for at selve figurens baggrund også er hvid
        fig.patch.set_facecolor('white')
        ax.set_facecolor('white')

        if vis_type == "Heatmap (Tendenser)":
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            if not passes.empty:
                kde = sns.kdeplot(
                    x=passes['LOCATIONX'],
                    y=passes['LOCATIONY'],
                    fill=True,
                    shade_lowest=False,
                    alpha=.6,
                    n_levels=10,
                    cmap='Reds', # 'Reds' ser godt ud på en hvid baggrund
                    ax=ax
                )
            st.info("Heatmap viser intensiteten af aktioner. Jo rødere, jo flere aktioner.")

        else:
            # Scatter plot af skud og pasninger
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            pitch.scatter(passes['LOCATIONX'], passes['LOCATIONY'], ax=ax, 
                          color='blue', alpha=0.3, s=20, label='Offensiv pasning')
            
            shots = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']
            pitch.scatter(shots['LOCATIONX'], shots['LOCATIONY'], ax=ax, 
                          color='red', s=120, edgecolors='black', marker='o', label='Skud')
            
            # Tilpas legend til hvid baggrund
            ax.legend(facecolor='white', edgecolor='black', loc='upper left')

        st.pyplot(fig)

    except Exception as e:
        st.error(f"Kunne ikke indlæse data: {e}")
        st.info("Sørg for at 'team_matches.csv' er uploadet til GitHub.")

# Kør funktionen hvis filen køres direkte
if __name__ == "__main__":
    vis_side()
