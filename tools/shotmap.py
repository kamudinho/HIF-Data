import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- KONFIGURATION ---
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'
# Din specifikke Opta ID for Hvidovre IF
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp=None):
    st.markdown(f"""
        <div style="background-color:{HIF_RED}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">🎯 HVIDOVRE IF - OPTA AFSLUTNINGER</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if not dp:
        st.error("Data pakke ikke fundet.")
        return

    # Hent rådata
    df_shots = dp.get('playerstats', pd.DataFrame())
    df_matches = dp.get('opta_matches', pd.DataFrame())

    if df_shots.empty:
        st.info("Ingen afslutninger fundet i databasen.")
        return

    # --- 1. FILTRERING: KUN HVIDOVRE SPIL_ID ---
    # Vi filtrerer på EVENT_CONTESTANT_OPTAUUID for at sikre det er HIF
    df_hif = df_shots[df_shots['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()

    if df_hif.empty:
        st.warning(f"Ingen data fundet for Hvidovre ID: {HIF_OPTA_UUID}")
        return

    # --- 2. UI LAYOUT ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        # Spiller filter
        spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste)
        
        vis_type = st.radio("Vis:", ["Alle skud", "Kun mål"], horizontal=True)

    # Filtrér data baseret på valg
    df_plot = df_hif.copy()
    if valgt_spiller != "Hele Holdet":
        df_plot = df_plot[df_plot['PLAYER_NAME'] == valgt_spiller]
    
    if vis_type == "Kun mål":
        df_plot = df_plot[df_plot['EVENT_OUTCOME'].astype(str) == '1']

    # --- 3. STATISTIK BOKS ---
    with col_stats:
        total_shots = len(df_plot)
        total_goals = len(df_plot[df_plot['EVENT_OUTCOME'].astype(str) == '1'])
        # xG_VAL beregnet i data_load.py
        total_xg = df_plot['XG_VAL'].sum() if 'XG_VAL' in df_plot.columns else 0
        
        st.markdown(f"""
        <div style="border-left: 5px solid {HIF_RED}; padding: 15px; background-color: #f8f9fa; border-radius: 4px; margin-top:20px;">
            <h4 style="margin:0; color:{HIF_RED};">{valgt_spiller}</h4>
            <hr>
            <p style="margin:0; font-size:1.2rem;"><b>{total_shots}</b> skud / <b>{total_goals}</b> mål</p>
            <p style="margin:0; font-size:1.2rem;"><b>{total_xg:.2f}</b> total xG</p>
        </div>
        """, unsafe_allow_html=True)

    # --- 4. TEGN KORTET ---
    with col_map:
        # Opta bruger 0-100 skala
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        # Golden Zone visualisering
        ax.add_patch(plt.Rectangle((37, 88.5), 26, 11.5, color='gold', alpha=0.1, zorder=1))

        if not df_plot.empty:
            for _, row in df_plot.iterrows():
                is_goal = str(row['EVENT_OUTCOME']) == '1'
                color = HIF_RED if is_goal else HIF_BLUE
                # Skalér cirklerne efter xG
                size = (row.get('XG_VAL', 0.05) * 1200) + 100
                # Trekant for hovedstød (Qualifier 15)
                marker = '^' if '15' in str(row.get('QUALIFIERS', '')) else 'o'
                
                pitch.scatter(row['EVENT_X'], row['EVENT_Y'], 
                              s=size, c=color, marker=marker,
                              edgecolors='white', linewidths=1,
                              ax=ax, alpha=0.8, zorder=3)
        
        st.pyplot(fig)
        st.caption("Cirkel = Fod | Trekant = Hovedstød | Størrelse = xG-værdi")
