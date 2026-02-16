import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import seaborn as sns
import matplotlib.pyplot as plt

def vis_side():
    st.markdown("### 🛡️ Taktisk Modstanderanalyse")
    
    try:
        # 1. Indlæs data
        df = pd.read_csv("data/team_matches.csv")
        
        st.sidebar.header("Analyse Indstillinger")
        valgt_kamp = st.sidebar.selectbox("Vælg Kamp", df['MATCHLABEL'].unique())
        kamp_data = df[df['MATCHLABEL'] == valgt_kamp]
        
        # 2. Overskrift og overordnede tal
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Aktioner", len(kamp_data))
        col_m2.metric("Egne Skud", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']))
        col_m3.metric("Skud imod", len(kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']))
        
        st.divider()

        # 3. Opsætning af tre kolonner til de tre baner
        col_pass, col_shot, col_against = st.columns(3)

        # Fælles Pitch-indstillinger
        pitch = VerticalPitch(
            pitch_type='wyscout', pitch_color='white', 
            line_color='#555555', linewidth=1.5
        )

        # --- KOLONNE 1: PASNINGER ---
        with col_pass:
            st.caption("🔥 Pasningsmønster")
            fig1, ax1 = pitch.draw(figsize=(4, 6))
            data = kamp_data[kamp_data['PRIMARYTYPE'] == 'pass']
            if not data.empty:
                sns.kdeplot(x=data['LOCATIONY'], y=data['LOCATIONX'], fill=True, 
                            alpha=.6, cmap='Reds', ax=ax1, clip=((0, 100), (0, 100)), linewidths=0)
                # Små pile for at indikere position
                pitch.arrows(data.LOCATIONX, data.LOCATIONY, data.LOCATIONX + 2, data.LOCATIONY, 
                             width=1.5, color='#3498db', ax=ax1, alpha=0.3)
            st.pyplot(fig1)

        # --- KOLONNE 2: EGNE SKUD ---
        with col_shot:
            st.caption("🎯 Egne Afslutninger")
            fig2, ax2 = pitch.draw(figsize=(4, 6))
            data = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot']
            if not data.empty:
                sns.kdeplot(x=data['LOCATIONY'], y=data['LOCATIONX'], fill=True, 
                            alpha=.6, cmap='YlOrBr', ax=ax2, clip=((0, 100), (0, 100)), linewidths=0)
                pitch.scatter(data.LOCATIONX, data.LOCATIONY, color='red', edgecolors='black', s=80, ax=ax2)
            st.pyplot(fig2)

        # --- KOLONNE 3: SKUD IMOD ---
        with col_against:
            st.caption("⚠️ Modstanderens Skud")
            fig3, ax3 = pitch.draw(figsize=(4, 6))
            data = kamp_data[kamp_data['PRIMARYTYPE'] == 'shot_against']
            if not data.empty:
                sns.kdeplot(x=data['LOCATIONY'], y=data['LOCATIONX'], fill=True, 
                            alpha=.6, cmap='Purples', ax=ax3, clip=((0, 100), (0, 100)), linewidths=0)
                pitch.scatter(data.LOCATIONX, data.LOCATIONY, color='purple', edgecolors='white', s=80, ax=ax3)
            st.pyplot(fig3)

    except Exception as e:
        st.error(f"Fejl: {e}")

if __name__ == "__main__":
    vis_side()
