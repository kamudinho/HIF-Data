import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import seaborn as sns
import matplotlib.pyplot as plt

def vis_side():
    st.markdown("### 🛡️ Taktisk Modstanderanalyse")
    st.markdown("Analyse af offensive mønstre og afslutninger.")

    try:
        df = pd.read_csv("data/team_matches.csv")
        
        st.sidebar.header("Analyse Indstillinger")
        valgt_kamp = st.sidebar.selectbox("Vælg Kamp", df['MATCHLABEL'].unique())
        kamp_data = df[df['MATCHLABEL'] == valgt_kamp]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Aktioner", len(kamp_data))
        col2.metric("Egne Skud", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']))
        col3.metric("Skud imod", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']))

        vis_type = st.radio("Visning:", ["Heatmap", "Scatter"], horizontal=True)

        # Opsætning af lille vertikal bane
        pitch = VerticalPitch(
            pitch_type='wyscout', 
            pitch_color='white', 
            line_color='#555555',
            linewidth=2
        )
        
        fig, ax = pitch.draw(figsize=(4, 6))
        fig.patch.set_facecolor('white')

        if vis_type == "Heatmap":
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            if not passes.empty:
                sns.kdeplot(
                    x=passes['LOCATIONY'], y=passes['LOCATIONX'],
                    fill=True, alpha=.7, n_levels=15, cmap='Reds',
                    ax=ax, clip=((0, 100), (0, 100)), linewidths=0
                )
        else:
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            pitch.scatter(passes.LOCATIONX, passes.LOCATIONY, ax=ax, 
                          color='#3498db', alpha=0.4, s=20, label='Pasning')
            
            shots = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']
            pitch.scatter(shots.LOCATIONX, shots.LOCATIONY, ax=ax, 
                          color='#e74c3c', s=100, edgecolors='black', label='Skud')
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, fontsize=8)

        # Centrer banen
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c2:
            st.pyplot(fig)

    except Exception as e:
        st.error(f"Fejl: {e}")

if __name__ == "__main__":
    vis_side()
