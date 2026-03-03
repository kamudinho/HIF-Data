import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt

# --- FARVER ---
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'

def vis_side(df_spillere=None):
    # --- TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:{HIF_RED}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; text-transform:uppercase; font-size:1.1rem;">HIF AFSLUTNINGER (OPTA DATA)</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # Hent data fra session_state (fra din get_opta_queries)
    df_raw = st.session_state.get("shotevents_data")
    
    if df_raw is None or df_raw.empty:
        st.info("Ingen Opta-afslutninger fundet.")
        return

    # --- 1. OPTA DATARENS ---
    df_s = df_raw.copy()
    
    # Opta skud-ID'er: 13 (Miss), 14 (Post), 15 (Saved), 16 (Goal)
    shot_types = ['13', '14', '15', '16']
    df_s = df_s[df_s['EVENT_TYPEID'].astype(str).isin(shot_types)].copy()
    
    # Mål-logik: EVENT_OUTCOME == 1 er mål i Opta
    df_s['IS_GOAL'] = df_s['EVENT_OUTCOME'].astype(str) == '1'
    
    # xG håndtering (Qualifier 321 eller 460 i Opta)
    df_s['SHOTXG'] = pd.to_numeric(df_s.get('EXPECTED_GOALS', 0), errors='coerce').fillna(0.1)

    # --- 2. UI & FILTRERING ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        spiller_liste = sorted(df_s['PLAYER_NAME'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=["Hele holdet"] + spiller_liste)
        
        df_p = df_s.copy() if valgt_spiller == "Hele holdet" else df_s[df_s['PLAYER_NAME'] == valgt_spiller]
        df_p = df_p.sort_values(by=['EVENT_TIMEMIN']).reset_index(drop=True)
        df_p['NR'] = df_p.index + 1

        # Stats boks
        total_xg = df_p['SHOTXG'].sum()
        st.metric("Total xG", f"{total_xg:.2f}")
        st.metric("Skud / Mål", f"{len(df_p)} / {int(df_p['IS_GOAL'].sum())}")

    with col_map:
        # pitch_type='opta' bruger 0-100 koordinater
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444', goal_type='box')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        # Danger Zone (Opta: X > 88.5, Y mellem 37 og 63)
        # Vi tegner den for at vise trænerne hvor de "dyre" chancer ligger
        ax.add_patch(plt.Rectangle((37, 88.5), 26, 11.5, color='orange', alpha=0.1, zorder=1))

        if not df_p.empty:
            for _, row in df_p.iterrows():
                color = HIF_RED if row['IS_GOAL'] else HIF_BLUE
                # Størrelse baseret på xG
                sc_size = (row['SHOTXG'] * 700) + 100
                
                # Opta bruger EVENT_X og EVENT_Y
                pitch.scatter(row['EVENT_X'], row['EVENT_Y'], s=sc_size, c=color, 
                              edgecolors='white', ax=ax, zorder=3, alpha=0.8)
                
                # Nummer på prikken
                ax.text(row['EVENT_Y'], row['EVENT_X'], str(int(row['NR'])), 
                        color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
        
        st.pyplot(fig)
