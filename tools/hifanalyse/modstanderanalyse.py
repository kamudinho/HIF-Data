import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package=None):
    # --- 1. UI & CSS STYLING ---
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem; }
            .stTabs { margin-top: 0px; }
            .stat-box { 
                background-color: #f8f9fa; 
                padding: 8px; 
                border-radius: 6px; 
                border-left: 4px solid #df003b; 
                margin-bottom: 5px;
                font-size: 0.85rem;
            }
            .pitch-label {
                text-align: center;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 5px;
                color: #333;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA-LOAD ---
    if "events_data" not in st.session_state:
        # Her antages det at data hentes via din eksisterende logik
        st.error("Data ikke fundet. Venligst indlæs data fra hovedmenuen.")
        return

    df_events = st.session_state["events_data"].copy()

    # --- 3. FILTER-RÆKKE (OVER TABS) ---
    col_h1, col_h2, col_empty = st.columns([1, 1, 2])
    
    with col_h1:
        hold_liste = sorted(df_events['HOMECONTESTANT_NAME'].unique())
        valgt_hold = st.selectbox("Vælg hold:", hold_liste, key="opp_team_sel")
    
    with col_h2:
        hold_uuid = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]['HOMECONTESTANT_OPTAUUID'].iloc[0]
        df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()
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

    # FANEN: MED BOLD (Store baner)
    with tabs[1]:
        c1, c2 = st.columns(2)
        pitch_half = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING (Egen halvdel)</p>', unsafe_allow_html=True)
            fig, ax = pitch_half.draw(figsize=(6, 8))
            ax.set_ylim(0, 50) 
            df_opbyg = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] < 50)]
            if not df_opbyg.empty:
                sns.kdeplot(x=df_opbyg['EVENT_Y'], y=df_opbyg['EVENT_X'], fill=True, cmap='Reds', 
                            alpha=0.6, levels=10, thresh=0.05, ax=ax, clip=((0, 100), (0, 50)))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        with c2:
            st.markdown('<p class="pitch-label">GENNEMBRUD (Modstander)</p>', unsafe_allow_html=True)
            fig, ax = pitch_half.draw(figsize=(6, 8))
            ax.set_ylim(50, 100)
            df_gen = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] >= 50)]
            if not df_gen.empty:
                sns.kdeplot(x=df_gen['EVENT_Y'], y=df_gen['EVENT_X'], fill=True, cmap='Reds', 
                            alpha=0.6, levels=10, thresh=0.05, ax=ax, clip=((0, 100), (50, 100)))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    # FANEN: MOD BOLD (Kompakt og med dueller)
    with tabs[2]:
        # Vi bruger smallere kolonner [1, 1, 1] for at gøre banen mindre
        c_left, c_mid, c_right = st.columns([1, 1, 1])
        
        with c_mid:
            st.markdown('<p class="pitch-label">DEFENSIV INTENSITET</p>', unsafe_allow_html=True)
            pitch_full = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch_full.draw(figsize=(4, 6)) # Mindre figsize
            
            # Vi filtrerer for både dueller og erobringer
            df_def = df_hold[df_hold['type'].isin(['duel', 'erobring'])]
            
            if not df_def.empty:
                sns.kdeplot(x=df_def['EVENT_Y'], y=df_def['EVENT_X'], fill=True, cmap='Blues', 
                            alpha=0.6, levels=15, thresh=0.05, ax=ax, clip=((0, 100), (0, 100)))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    # FANEN: TOP 5
    with tabs[3]:
        st.markdown(f"#### Top 5 præstationer: {valgt_hold}")
        stat_cols = st.columns(3)
        for i, (kat_id, kat_navn) in enumerate([('pass', 'Afleveringer'), ('duel', 'Dueller'), ('erobring', 'Erobringer')]):
            with stat_cols[i]:
                st.markdown(f"**{kat_navn}**")
                top = df_hold[df_hold['type'] == kat_id]['PLAYER_NAME'].value_counts().head(5)
                for navn, count in top.items():
                    st.markdown(f'<div class="stat-box"><b>{count}</b> {navn}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
