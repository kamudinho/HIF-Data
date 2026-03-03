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
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">HVIDOVRE IF - OFFENSIV ANALYSE</h3>
        </div>
    """, unsafe_allow_html=True)
    
    df_raw = dp.get('playerstats', pd.DataFrame())
    if df_raw.empty:
        st.info("Ingen data fundet.")
        return

    # --- 1. DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    df_hif['TYPE_CLEAN'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip().str.upper()
    
    # --- 2. TABS & FILTRE ---
    tab1, tab2 = st.tabs(["Skudkort", "Assists"])

    # Spiller-dropdown placeret over kortet
    spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste)

    # --- TAB 1: SKUDKORT ---
    with tab1:
        col_map, col_stats = st.columns([2.2, 1])
        
        # Filtrer skudtyper (13: Miss, 14: Post, 15: Saved, 16: Goal, G/PG: Goal)
        skud_typer = ['13', '14', '15', '16', 'G', 'PG', '38']
        df_skud = df_hif[df_hif['TYPE_CLEAN'].isin(skud_typer)].copy()
        
        if valgt_spiller != "Hele Holdet":
            df_skud = df_skud[df_skud['PLAYER_NAME'] == valgt_spiller]

        # Definer mål (Rød) vs ikke-mål (Blå)
        df_skud['ER_MAAL'] = df_skud['TYPE_CLEAN'].isin(['16', 'G', 'PG'])

        with col_map:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444')
            fig, ax = pitch.draw(figsize=(8, 10))
            
            if not df_skud.empty:
                for _, row in df_skud.iterrows():
                    color = HIF_RED if row['ER_MAAL'] else HIF_BLUE
                    size = (float(row.get('XG_VAL', 0.1)) * 1500) + 100
                    # Kun cirkler (ingen ikoner/trekanter)
                    pitch.scatter(row['EVENT_X'], row['EVENT_Y'], s=size, c=color, 
                                  edgecolors='white', ax=ax, alpha=0.7, zorder=3)
            st.pyplot(fig)

        with col_stats:
            st.markdown(f"**Statistik for {valgt_spiller}**")
            st.write(f"Skud i alt: {len(df_skud)}")
            st.write(f"Mål: {int(df_skud['ER_MAAL'].sum())}")
            st.write(f"Total xG: {df_skud['XG_VAL'].sum():.2f}")

    # --- TAB 2: ASSISTS ---
    with tab2:
        col_map_a, col_stats_a = st.columns([2.2, 1])
        
        # Filtrer assists (Type AS eller Qualifier 210/154)
        df_assists = df_hif[
            (df_hif['TYPE_CLEAN'] == 'AS') | 
            (df_hif['QUALIFIERS'].astype(str).str.contains('210|154', na=False))
        ].copy()

        if valgt_spiller != "Hele Holdet":
            df_assists = df_assists[df_assists['PLAYER_NAME'] == valgt_spiller]

        with col_map_a:
            pitch_a = VerticalPitch(pitch_type='opta', line_color='#444444')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
            
            if not df_assists.empty:
                for _, row in df_assists.iterrows():
                    # Tegner en simpel pil for assisten (Guld)
                    # Hvis PASS_END_X/Y ikke findes, tegnes kun startpunktet
                    ex = row.get('PASS_END_X', 95)
                    ey = row.get('PASS_END_Y', 50)
                    pitch_a.arrows(row['EVENT_X'], row['EVENT_Y'], ex, ey, 
                                   color='gold', width=2, headwidth=4, ax=ax_a)
                    pitch_a.scatter(row['EVENT_X'], row['EVENT_Y'], color='gold', s=100, ax=ax_a)
            st.pyplot(fig_a)

        with col_stats_a:
            st.markdown(f"**Assists for {valgt_spiller}**")
            st.write(f"Antal assists: {len(df_assists)}")
            if not df_assists.empty:
                st.dataframe(df_assists[['PLAYER_NAME', 'TYPE_CLEAN']].rename(columns={'TYPE_CLEAN': 'Type'}))
