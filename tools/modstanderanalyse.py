import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import seaborn as sns
import matplotlib.pyplot as plt

def vis_side():
    st.markdown("Analyse af offensive mønstre og afslutninger.")

    try:
        df = pd.read_csv("data/team_matches.csv")
        
        st.sidebar.header("Analyse Indstillinger")
        valgt_kamp = st.sidebar.selectbox("Vælg Kamp/Modstander", df['MATCHLABEL'].unique())
        
        kamp_data = df[df['MATCHLABEL'] == valgt_kamp]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Offensive Aktioner", len(kamp_data))
        with col2:
            st.metric("Egne Skud", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']))
        with col3:
            st.metric("Skud imod", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']))

        vis_type = st.radio(
            "Vælg visuel analyse:", 
            ["Heatmap (Tendenser)", "Scatter (Enkelte aktioner)"], 
            horizontal=True
        )

        # 1. 'vertical=True' gør banen lodret
        pitch = Pitch(
            pitch_type='wyscout', 
            pitch_color='white', 
            line_color='#555555',
            linewidth=2,
            vertical=True  
        )
        
        # 2. Mindre figsize og byttet om på bredde/højde (f.eks. 5 bred, 7 høj)
        fig, ax = pitch.draw(figsize=(5, 7))
        fig.patch.set_facecolor('white')

        if vis_type == "Heatmap (Tendenser)":
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            if not passes.empty:
                # Ved vertical=True skal x og y byttes i sns.kdeplot for at det matcher banen
                sns.kdeplot(
                    y=passes['LOCATIONX'],
                    x=passes['LOCATIONY'],
                    fill=True,
                    alpha=.6,
                    n_levels=15,
                    cmap='Reds',
                    ax=ax,
                    clip=((0, 100), (0, 100)) 
                )
        else:
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            # pitch.scatter håndterer selv vertical=True, så vi sender bare x, y som normalt
            pitch.scatter(
                passes['LOCATIONX'], passes['LOCATIONY'], 
                ax=ax, color='#3498db', alpha=0.4, s=30, 
                label='Offensiv pasning'
            )
            
            shots = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']
            pitch.scatter(
                shots['LOCATIONX'], shots['LOCATIONY'], 
                ax=ax, color='#e74c3c', s=120, 
                edgecolors='black', marker='o', label='Skud'
            )
            ax.legend(facecolor='white', edgecolor='black', loc='upper left', fontsize=8)

        # Centrer billedet i Streamlit ved hjælp af kolonner
        col_left, col_mid, col_right = st.columns([1, 2, 1])
        with col_mid:
            st.pyplot(fig)

    except Exception as e:
        st.error(f"Fejl ved indlæsning af data: {e}")

if __name__ == "__main__":
    vis_side()
