import streamlit as st
import pandas as pd
from mplsoccer import Pitch
import seaborn as sns
import matplotlib.pyplot as plt

def vis_side():
    st.markdown("Analyse af offensive mønstre og afslutninger.")

    # 1. Indlæs data
    try:
        # Sørg for at stien passer til din GitHub-struktur
        df = pd.read_csv("data/team_matches.csv")
        
        # 2. Sidebar filtre
        st.sidebar.header("Analyse Indstillinger")
        valgt_kamp = st.sidebar.selectbox("Vælg Kamp/Modstander", df['MATCHLABEL'].unique())
        
        # Filtrer data for den valgte kamp
        kamp_data = df[df['MATCHLABEL'] == valgt_kamp]
        
        # 3. Layout med kolonner til hurtige tal
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Offensive Aktioner", len(kamp_data))
        with col2:
            st.metric("Egne Skud", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']))
        with col3:
            st.metric("Skud imod", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']))

        # 4. Valg af visning via Radio knap
        vis_type = st.radio(
            "Vælg visuel analyse:", 
            ["Heatmap (Tendenser)", "Scatter (Enkelte aktioner)"], 
            horizontal=True
        )

        # 5. Opsætning af banen (Hvid baggrund)
        pitch = Pitch(
            pitch_type='wyscout', 
            pitch_color='white', 
            line_color='#555555',
            linewidth=2
        )
        fig, ax = pitch.draw(figsize=(10, 7))
        fig.patch.set_facecolor('white')

        # 6. Tegning baseret på brugerens valg
        if vis_type == "Heatmap (Tendenser)":
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            if not passes.empty:
                # clip=((x_min, x_max), (y_min, y_max)) holder det inden for kridtstregerne
                sns.kdeplot(
                    x=passes['LOCATIONX'],
                    y=passes['LOCATIONY'],
                    fill=True,
                    alpha=.6,
                    n_levels=15,
                    cmap='Reds',
                    ax=ax,
                    clip=((0, 100), (0, 100)) 
                )
            else:
                st.warning("Ingen pasningsdata fundet for denne kamp.")

        else:
            # Scatter plot af skud og pasninger
            passes = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            pitch.scatter(
                passes['LOCATIONX'], passes['LOCATIONY'], 
                ax=ax, color='#3498db', alpha=0.4, s=30, 
                label='Offensiv pasning', edgecolors='none'
            )
            
            shots = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']
            pitch.scatter(
                shots['LOCATIONX'], shots['LOCATIONY'], 
                ax=ax, color='#e74c3c', s=150, 
                edgecolors='black', marker='o', label='Skud'
            )
            
            ax.legend(facecolor='white', edgecolor='black', loc='upper left', fontsize=10)
            st.info("💡 Scatter viser de præcise positioner for hver offensiv aktion.")

        # Vis figuren i Streamlit
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Fejl ved indlæsning af data: {e}")
        st.info("Tjek at data/team_matches.csv findes og er korrekt formateret.")

if __name__ == "__main__":
    vis_side()
