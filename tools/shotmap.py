import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- KONFIGURATION ---
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp=None):
    st.markdown(f"""
        <div style="background-color:{HIF_RED}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">🎯 HVIDOVRE IF - OPTA SKUDKORT</h3>
        </div>
    """, unsafe_allow_html=True)
    
    df_shots = dp.get('playerstats', pd.DataFrame())

    if df_shots.empty:
        st.info("Ingen afslutninger fundet.")
        return

    # --- 1. FILTRERING & KORREKT MÅL-TÆLLING ---
    df_hif = df_shots[df_shots['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Konverter TYPEID til string for sikker sammenligning
    df_hif['EVENT_TYPEID'] = df_hif['EVENT_TYPEID'].astype(str).str.strip()
    
    # DEFINITION AF MÅL: Type 16, G, PG eller OG
    maal_typer = ['16', 'G', 'PG', 'OG']
    df_hif['ER_MAAL'] = df_hif['EVENT_TYPEID'].isin(maal_typer)

    # --- 2. LAYOUT ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste)
        vis_type = st.radio("Vis:", ["Alle skud", "Kun mål"], horizontal=True)

    # Filtrér data til visning
    df_plot = df_hif.copy()
    if valgt_spiller != "Hele Holdet":
        df_plot = df_plot[df_plot['PLAYER_NAME'] == valgt_spiller]
    
    if vis_type == "Kun mål":
        df_plot = df_plot[df_plot['ER_MAAL'] == True]

    # --- 3. STATS BOKS ---
    with col_stats:
        total_skud = len(df_plot)
        total_maal = int(df_plot['ER_MAAL'].sum())
        total_xg = df_plot['XG_VAL'].sum()

        st.markdown(f"""
        <div style="border-left: 5px solid {HIF_RED}; padding: 15px; background-color: #f8f9fa; border-radius: 4px; margin-top:20px;">
            <h4 style="margin:0; color:{HIF_RED};">{valgt_spiller}</h4>
            <hr>
            <p style="margin:0; font-size:1.1rem;"><b>Skud:</b> {total_skud}</p>
            <p style="margin:0; font-size:1.1rem; color:{HIF_RED if total_maal > 0 else 'black'};"><b>Mål:</b> {total_maal}</p>
            <p style="margin:0; font-size:1.1rem;"><b>xG i alt:</b> {total_xg:.2f}</p>
        </div>
        """, unsafe_allow_html=True)

    # --- 4. TEGN KORTET ---
    with col_map:
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        # Golden Zone
        ax.add_patch(plt.Rectangle((37, 88.5), 26, 11.5, color='gold', alpha=0.1, zorder=1))

        if not df_plot.empty:
            for _, row in df_plot.iterrows():
                # Farve: Rød for mål, Blå for Miss/Saved/Post
                color = HIF_RED if row['ER_MAAL'] else HIF_BLUE
                
                # Størrelse baseret på xG
                size = (row.get('XG_VAL', 0.05) * 1200) + 100
                
                # Marker: Trekant for hovedstød (Qualifier 15)
                marker = '^' if '15' in str(row.get('QUALIFIERS', '')) else 'o'
                
                pitch.scatter(row['EVENT_X'], row['EVENT_Y'], 
                              s=size, c=color, marker=marker,
                              edgecolors='white', linewidths=1,
                              ax=ax, alpha=0.8, zorder=3)
        
        st.pyplot(fig)
