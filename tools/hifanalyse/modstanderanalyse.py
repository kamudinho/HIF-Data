import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import matplotlib.patches as patches

def vis_side(analysis_package=None):
    # --- 1. UI & CSS STYLING ---
    st.markdown("""
        <style>
            /* Gør tabs og dropdowns mere kompakte og strømlinede */
            .stTabs { margin-top: -10px; }
            .stat-box { 
                background-color: #f8f9fa; 
                padding: 8px; 
                border-radius: 6px; 
                border-left: 4px solid #df003b; 
                margin-bottom: 5px;
                font-size: 0.85rem;
            }
            /* Justering af overskrifter på banerne */
            .pitch-label {
                text-align: center;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 5px;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA-LOAD SIKRING ---
    if "events_data" not in st.session_state:
        st.warning("Data ikke fundet i systemet. Venligst gå til hovedmenuen for at indlæse data.")
        return

    df_events = st.session_state["events_data"].copy()

    # --- 3. TOPBAR: TABS TIL VENSTRE, DROPDOWNS TIL HØJRE ---
    # Vi laver en container til topmenuen
    menu_col1, menu_col2, menu_col3 = st.columns([2.5, 1, 1])
    
    with menu_col1:
        tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with menu_col2:
        hold_liste = sorted(df_events['HOMECONTESTANT_NAME'].unique())
        valgt_hold = st.selectbox("Hold:", hold_liste, key="opp_team_sel", label_visibility="collapsed")
    
    with menu_col3:
        # Find data for valgt hold
        hold_uuid = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]['HOMECONTESTANT_OPTAUUID'].iloc[0]
        df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()
        
        spiller_liste = ["Alle spillere"] + sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Spiller:", spiller_liste, label_visibility="collapsed")

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    # Mapping
    def map_type(tid):
        if tid == 1: return 'pass'
        if tid in [4, 5]: return 'duel'
        if tid in [8, 49]: return 'erobring'
        return 'other'
    df_hold['type'] = df_hold['EVENT_TYPEID'].apply(map_type)

    # --- 4. FANER ---
    
    # FANEN: GRUNDSTRUKTUR
    with tabs[0]:
        st.write(f"Analyse-setup for {valgt_hold}")

    # FANEN: MED BOLD
    with tabs[1]:
        c1, c2 = st.columns(2)
        
        # --- VENSTRE: OPBYGNING (Egen halvdel - Mål nederst) ---
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING (Egen halvdel)</p>', unsafe_allow_html=True)
            # Vi bruger half=True, men koordinaterne 0-50 skal vises i bunden.
            # Ved at bruge 'opta' og lade tallene være, men vende aksen, får vi målet ned.
            pitch_own = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch_own.draw(figsize=(4, 6))
            ax.set_ylim(0, 50) # Viser 0 (mål) nederst til 50 (midte) øverst
            
            df_opbyg = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] < 50)]
            if not df_opbyg.empty:
                sns.kdeplot(x=df_opbyg['EVENT_Y'], y=df_opbyg['EVENT_X'], fill=True, cmap='Reds', 
                            alpha=0.6, levels=10, thresh=0.05, ax=ax, clip=((0, 100), (0, 50)))
            st.pyplot(fig)
            plt.close(fig)

        # --- HØJRE: GENNEMBRUD (Modstander - Mål øverst) ---
        with c2:
            st.markdown('<p class="pitch-label">GENNEMBRUD (Modstander)</p>', unsafe_allow_html=True)
            pitch_opp = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch_opp.draw(figsize=(4, 6))
            ax.set_ylim(50, 100) # Viser 50 (midte) nederst til 100 (mål) øverst
            
            df_gen = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] >= 50)]
            if not df_gen.empty:
                sns.kdeplot(x=df_gen['EVENT_Y'], y=df_gen['EVENT_X'], fill=True, cmap='Reds', 
                            alpha=0.6, levels=10, thresh=0.05, ax=ax, clip=((0, 100), (50, 100)))
            st.pyplot(fig)
            plt.close(fig)

    # FANEN: MOD BOLD
    with tabs[2]:
        st.markdown('<p class="pitch-label">DEFENSIV INTENSITET (Fuld bane)</p>', unsafe_allow_html=True)
        pitch_full = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#333333')
        fig, ax = pitch_full.draw(figsize=(8, 10))
        
        df_def = df_hold[df_hold['type'].isin(['duel', 'erobring'])]
        if not df_def.empty:
            sns.kdeplot(x=df_def['EVENT_Y'], y=df_def['EVENT_X'], fill=True, cmap='Blues', 
                        alpha=0.6, levels=15, thresh=0.05, ax=ax, clip=((0, 100), (0, 100)))
        st.pyplot(fig)
        plt.close(fig)

    # FANEN: TOP 5
    with tabs[3]:
        st.markdown(f"#### Top 5 - {valgt_hold}")
        c1, c2, c3 = st.columns(3)
        kat_list = [('pass', 'Afleveringer', c1), ('duel', 'Dueller', c2), ('erobring', 'Erobringer', c3)]
        
        for k_id, k_navn, col in kat_list:
            with col:
                st.markdown(f"**{k_navn}**")
                top = df_hold[df_hold['type'] == k_id]['PLAYER_NAME'].value_counts().head(5)
                for navn, count in top.items():
                    st.markdown(f'<div class="stat-box"><b>{count}</b> {navn}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
