import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#ffd700'
HIF_DARK = '#1a1a1a'
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # Data check
    df_raw = dp.get('playerstats', pd.DataFrame()) if isinstance(dp, dict) else dp
    if df_raw.empty:
        st.info("⚽ Ingen kampdata tilgængelig for den valgte periode.")
        return

    # --- DATA RENS & FILTRERING ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Sikker streng-håndtering (undgår 'Series object has no attribute strip' fejlen)
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)
    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt').astype(str)

    # --- TOP BAR: SPILLERVALG ---
    st.markdown("### 📊 Præstationsanalyse")
    spiller_liste = sorted(df_hif['PLAYER_NAME'].unique().tolist())
    valgt_spiller = st.selectbox("Vælg Profil", options=["Hele Holdet"] + spiller_liste, index=0)

    tab1, tab2 = st.tabs(["🎯 AFSLUTNINGER", "🅰️ ASSISTS & CREATION"])

    # --- TAB 1: SKUDKORT (xG DESIGN) ---
    with tab1:
        df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
        if valgt_spiller != "Hele Holdet":
            df_skud = df_skud[df_skud['PLAYER_NAME'] == valgt_spiller]

        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Pitch design: Mørkt og moderne
            pitch = VerticalPitch(half=True, pitch_type='opta', 
                                  pitch_color=HIF_DARK, line_color='#555555',
                                  goal_type='box', goal_alpha=0.8)
            fig, ax = pitch.draw(figsize=(10, 12))
            
            if not df_skud.empty:
                df_skud['ER_MAAL'] = df_skud['TYPE_STR'] == '16'
                
                # Plot xG cirkler (Størrelse baseret på xG)
                # Vi bruger 'XG_VAL' som vi lavede i data_load.py
                sc = pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'],
                                   s=(df_skud['XG_VAL'] * 1200) + 80,
                                   c=df_skud['ER_MAAL'].map({True: HIF_RED, False: 'white'}),
                                   edgecolors=HIF_RED, linewidth=1, alpha=0.7, ax=ax)
            st.pyplot(fig)

        with col2:
            st.markdown("#### Stats")
            total_skud = len(df_skud)
            maal = int(df_skud['TYPE_STR'] == '16').sum() if not df_skud.empty else 0
            total_xg = df_skud['XG_VAL'].sum() if not df_skud.empty else 0.0
            
            st.metric("Skud total", total_skud)
            st.metric("Mål", maal, delta=f"{maal - total_xg:+.2f} vs xG", delta_color="normal")
            st.metric("xG Total", f"{total_xg:.2f}")
            st.caption("Cirkelstørrelse indikerer xG værdi (sandsynlighed for mål).")

    # --- TAB 2: ASSISTS (CREATION DESIGN) ---
    with tab2:
        # Qualifier 210 = Assist, 211 = Second Assist (Pre-assist)
        df_a = df_hif[df_hif['QUAL_STR'].str.contains('210', na=False)].copy()
        if valgt_spiller != "Hele Holdet":
            df_a = df_a[df_a['PLAYER_NAME'] == valgt_spiller]

        col1, col2 = st.columns([3, 1])
        with col1:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color=HIF_DARK, line_color='#555555')
            fig_a, ax_a = pitch_a.draw(figsize=(10, 12))
            
            if not df_a.empty:
                # Elegante pile med guld-hoveder
                pitch_a.arrows(df_a['EVENT_X'], df_a['EVENT_Y'],
                               df_a['PASS_END_X'].fillna(98), df_a['PASS_END_Y'].fillna(50),
                               color=HIF_GOLD, width=3, headwidth=4, headlength=4, ax=ax_a, alpha=0.8)
                
                pitch_a.scatter(df_a['EVENT_X'], df_a['EVENT_Y'], 
                                s=120, color=HIF_DARK, edgecolors=HIF_GOLD, linewidth=2, ax=ax_a)
            st.pyplot(fig_a)

        with col2:
            st.markdown("#### Creation")
            st.metric("Assists", len(df_a))
            # Her kan du tilføje 'Key Passes' (skabte chancer der ikke blev mål) 
            # hvis du i SQL filtrerer på Qualifier 29
            st.caption("Pile viser afleveringens vej frem til assist.")
