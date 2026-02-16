import streamlit as st
from mplsoccer import VerticalPitch
import seaborn as sns
import matplotlib.pyplot as plt

def vis_side(df_live, hold_map):
    st.header("Taktisk Modstanderanalyse")

    if not df_live.empty:
        # Map holdnavne
        df_live['HOLD_NAVN'] = df_live['TEAM_WYID'].astype(str).map(hold_map).fillna(df_live['TEAM_WYID'].astype(str))
        
        # Sidebar uden ikoner
        alle_hold = sorted(df_live['HOLD_NAVN'].unique())
        valgt_hold = st.sidebar.selectbox("Vælg modstander", alle_hold)
        hold_data = df_live[df_live['HOLD_NAVN'] == valgt_hold]

        # Metrics uden ikoner
        c1, c2, c3 = st.columns(3)
        c1.metric("Aktioner", len(hold_data))
        c2.metric("Skud", len(hold_data[hold_data['PRIMARYTYPE'] == 'shot']))
        c3.metric("Skud imod", len(hold_data[hold_data['PRIMARYTYPE'] == 'shot_against']))

        st.divider()

        # Konfiguration af baner
        # Vi fjerner unødig luft med pad og gør linjerne tyndere (linewidth=0.5)
        pitch = VerticalPitch(
            pitch_type='wyscout', 
            pitch_color='white', 
            line_color='#888888',
            linewidth=0.5,
            pad_top=0, pad_bottom=0, pad_left=0, pad_right=0
        )
        
        cols = st.columns(3)
        # Definitioner uden ikoner
        configs = [
            ('pass', 'Offensive Pasninger', 'Reds'),
            ('shot', 'Egne Skud', 'YlOrBr'),
            ('shot_against', 'Skud Imod', 'Purples')
        ]

        for i, (p_type, title, cmap) in enumerate(configs):
            with cols[i]:
                # Centreret tekst uden ikoner
                st.markdown(f"<p style='text-align:center; font-size:13px; font-weight:bold; margin-bottom:-10px;'>{title.upper()}</p>", unsafe_allow_html=True)
                
                # Meget lille figsize for at tvinge banerne ned i størrelse
                fig, ax = pitch.draw(figsize=(1.8, 2.8))
                
                d = hold_data[hold_data['PRIMARYTYPE'] == p_type]
                if not d.empty:
                    # Heatmap
                    sns.kdeplot(
                        x=d['LOCATIONY'], y=d['LOCATIONX'], 
                        fill=True, alpha=.5, cmap=cmap, ax=ax, 
                        levels=6, thresh=.05, bw_adjust=0.8
                    )
                    # Små diskrete scatter-punkter til skud
                    if p_type != 'pass':
                        pitch.scatter(d.LOCATIONX, d.LOCATIONY, s=10, edgecolors='#333333', linewidth=0.3, c='white', alpha=0.8, ax=ax)
                
                st.pyplot(fig, use_container_width=False)
    else:
        st.info("Ingen data fundet.")
