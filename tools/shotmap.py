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
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">🎯 HVIDOVRE IF - OPTA ANALYSE</h3>
        </div>
    """, unsafe_allow_html=True)
    
    df_raw = dp.get('playerstats', pd.DataFrame())

    if df_raw.empty:
        st.info("Ingen data fundet.")
        return

    # --- 1. BENHÅRD RENSNING AF DATA ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Vi fjerner alt tvivl om typer: konverter til streng, fjern .0, og gør det til store bogstaver
    df_hif['TYPE_CLEAN'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip().str.upper()
    
    # DEFINITION AF MÅL (Baseret på din liste: 16, G, PG, OG)
    # Vi tjekker også for 38 (Temp_Goal) for en sikkerheds skyld
    maal_koder = ['16', 'G', 'PG', 'OG', '38']
    df_hif['ER_MAAL'] = df_hif['TYPE_CLEAN'].isin(maal_koder)

    # --- 2. UI LAYOUT ---
    col_map, col_stats = st.columns([2.2, 1])

    with col_stats:
        spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste)
        
        # Filtrering af data baseret på valg
        df_plot = df_hif.copy()
        if valgt_spiller != "Hele Holdet":
            df_plot = df_plot[df_plot['PLAYER_NAME'] == valgt_spiller]

        # Statistik beregning
        total_skud = len(df_plot)
        total_maal = int(df_plot['ER_MAAL'].sum())
        total_xg = df_plot['XG_VAL'].sum()

        st.markdown(f"""
        <div style="border-left: 5px solid {HIF_RED}; padding: 15px; background-color: #f8f9fa; border-radius: 4px; margin-top:10px;">
            <h4 style="margin:0;">{valgt_spiller}</h4>
            <hr>
            <h2 style="margin:0; color:{HIF_RED};">{total_skud} skud / {total_maal} mål</h2>
            <p>Total xG: <b>{total_xg:.2f}</b></p>
        </div>
        """, unsafe_allow_html=True)

    # --- 3. TEGN KORTET ---
    with col_map:
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444')
        fig, ax = pitch.draw(figsize=(8, 10))
        
        if not df_plot.empty:
            # Sorter så mål tegnes øverst (zorder)
            df_plot = df_plot.sort_values('ER_MAAL')
            
            for _, row in df_plot.iterrows():
                color = HIF_RED if row['ER_MAAL'] else HIF_BLUE
                # Vi bruger XG_VAL til størrelse, men sætter en minimumstørrelse
                size = (float(row['XG_VAL']) * 1500) + 100
                
                pitch.scatter(row['EVENT_X'], row['EVENT_Y'], 
                              s=size, c=color, edgecolors='white', 
                              ax=ax, alpha=0.7, zorder=4 if row['ER_MAAL'] else 3)
        st.pyplot(fig)

    # --- 4. DEBUG TABEL (Fjern denne når det virker) ---
    st.write("---")
    st.subheader("Debug: Hvad ser systemet?")
    debug_df = df_plot[['PLAYER_NAME', 'TYPE_CLEAN', 'ER_MAAL', 'XG_VAL']].copy()
    st.dataframe(debug_df.head(20))
