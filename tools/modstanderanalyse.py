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
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Aktioner", len(kamp_data))
        col2.metric("Egne Skud", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']))
        col3.metric("Skud imod", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']))

        vis_type = st.radio("Visning:", ["Heatmap", "Scatter"], horizontal=True)

        # 1. Definer Pitch UDEN vertical her
        pitch = Pitch(
            pitch_type='wyscout', 
            pitch_color='white', 
            line_color='#555555',
            linewidth=2
        )
        
        # 2. Tegn banen VERTIKALT her (6 høj, 4 bred for at gøre den lille)
        fig, ax = pitch.draw(figsize=(4, 6), vertical=True)
        fig.patch.set_facecolor('white')

        if vis_type == "Heatmap":
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            if not passes.empty:
                # Ved vertikal visning i mplsoccer/seaborn skal vi bytte om:
                # Wyscout Y (bredde) på x-aksen, Wyscout X (længde) på y-aksen
                sns.kdeplot(
                    x=passes['LOCATIONY'], 
                    y=passes['LOCATIONX'],
                    fill=True,
                    alpha=.6,
                    n_levels=15,
                    cmap='Reds',
                    ax=ax,
                    clip=((0, 100), (0, 100)) 
                )
        else:
            # Scatter (vi skal fortælle pitch.scatter at det er vertikalt)
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            pitch.scatter(passes.LOCATIONX, passes.LOCATIONY, ax=ax, 
                          color='#3498db', alpha=0.4, s=20, label='Pasning', vertical=True)
            
            shots = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']
            pitch.scatter(shots.LOCATIONX, shots.LOCATIONY, ax=ax, 
                          color='#e74c3c', s=80, edgecolors='black', label='Skud', vertical=True)
            
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=8)

        # Centrer det lille billede i Streamlit
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.pyplot(fig)

    except Exception as e:
        st.error(f"Fejl: {e}")

if __name__ == "__main__":
    vis_side()
