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
            .stTabs { margin-top: -30px; }
            .stat-box { 
                background-color: #f8f9fa; 
                padding: 8px; 
                border-radius: 6px; 
                border-left: 4px solid #df003b; 
                margin-bottom: 5px;
                font-size: 0.85rem;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA-LOAD ---
    if "events_data" not in st.session_state:
        # (Sørg for at din Snowflake-forbindelse er aktiv her)
        st.warning("Data ikke fundet. Genindlæser...")
        return

    df_events = st.session_state["events_data"].copy()

    # --- 3. FILTRERING ---
    hold_liste = sorted(df_events['HOMECONTESTANT_NAME'].unique())
    col_sel, col_spiller = st.columns([1, 1])
    with col_sel:
        valgt_hold = st.selectbox("Vælg hold:", hold_liste, key="opp_team_sel")
    
    hold_info = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]
    hold_uuid = hold_info['HOMECONTESTANT_OPTAUUID'].iloc[0]
    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()

    with col_spiller:
        spiller_liste = ["Alle spillere"] + sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Filter spiller:", spiller_liste)

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    # Mapping
    def map_type(tid):
        if tid == 1: return 'pass'
        if tid in [4, 5]: return 'duel'
        if tid in [8, 49]: return 'erobring'
        return 'other'
    df_hold['type'] = df_hold['EVENT_TYPEID'].apply(map_type)

    # --- 4. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]:
        st.info("Her kan du indsætte generel hold-info eller formationstaktik.")

    with tabs[1]:
        # MED BOLD: To halve baner ved siden af hinanden
        col1, col2 = st.columns(2)
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        
        with col1:
            st.markdown("<p style='text-align:center; font-weight:bold;'>OPBYGNING (Egen halvdel)</p>", unsafe_allow_html=True)
            fig, ax = pitch.draw(figsize=(4, 6))
            # Spejling af egen halvdel (0-50) så målet er nederst (visuelt 100)
            df_opbyg = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] < 50)].copy()
            df_opbyg['EVENT_X'] = 100 - df_opbyg['EVENT_X']
            df_opbyg['EVENT_Y'] = 100 - df_opbyg['EVENT_Y']
            
            if not df_opbyg.empty:
                sns.kdeplot(x=df_opbyg['EVENT_Y'], y=df_opbyg['EVENT_X'], fill=True, cmap='Reds', 
                            alpha=0.6, levels=10, thresh=0.05, ax=ax, clip=((0, 100), (50, 100)))
            st.pyplot(fig)
            plt.close(fig)

        with col2:
            st.markdown("<p style='text-align:center; font-weight:bold;'>GENNEMBRUD (Modstander)</p>", unsafe_allow_html=True)
            fig, ax = pitch.draw(figsize=(4, 6))
            # Standard visning af modstanders halvdel (50-100)
            df_gen = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] >= 50)].copy()
            if not df_gen.empty:
                sns.kdeplot(x=df_gen['EVENT_Y'], y=df_gen['EVENT_X'], fill=True, cmap='Reds', 
                            alpha=0.6, levels=10, thresh=0.05, ax=ax, clip=((0, 100), (50, 100)))
            st.pyplot(fig)
            plt.close(fig)

    with tabs[2]:
        # MOD BOLD: Fuld bane med præcis clipping
        st.markdown("<p style='text-align:center; font-weight:bold;'>DEFENSIV INTENSITET (Dueller & Erobringer)</p>", unsafe_allow_html=True)
        pitch_full = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#333333')
        fig, ax = pitch_full.draw(figsize=(8, 10))
        
        df_def = df_hold[df_hold['type'].isin(['duel', 'erobring'])]
        if not df_def.empty:
            sns.kdeplot(x=df_def['EVENT_Y'], y=df_def['EVENT_X'], fill=True, cmap='Blues', 
                        alpha=0.6, levels=15, thresh=0.05, ax=ax, clip=((0, 100), (0, 100)))
        st.pyplot(fig)
        plt.close(fig)

    with tabs[3]:
        st.markdown(f"#### Top præstationer: {valgt_hold}")
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
