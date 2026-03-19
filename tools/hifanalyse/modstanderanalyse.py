import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

def vis_side(analysis_package=None):
    # --- 1. UI & CSS STYLING ---
    st.markdown("""
        <style>
            /* Gør layoutet bredere og fjern unødig padding */
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
                font-size: 16px;
                margin-bottom: 5px;
                color: #333;
            }
            /* Styling af dropdown-rækken */
            .filter-row {
                background-color: #ffffff;
                padding: 10px 0px;
                margin-bottom: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA-LOAD SIKRING ---
    if "events_data" not in st.session_state:
        try:
            from data.data_load import _get_snowflake_conn
            conn = _get_snowflake_conn()
            query = """
            SELECT 
                HOMECONTESTANT_NAME, HOMECONTESTANT_OPTAUUID,
                EVENT_CONTESTANT_OPTAUUID, EVENT_TYPEID, 
                EVENT_X, EVENT_Y, PLAYER_NAME
            FROM KLUB_HVIDOVREIF.AXIS.OPTA_EVENTS
            WHERE COMPETITION_OPTAUUID = '6ifaeunfdelecgticvxanikzu'
            AND TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'
            AND EVENT_TYPEID IN (1, 4, 5, 8, 49)
            """
            st.session_state["events_data"] = conn.query(query)
        except Exception as e:
            st.error(f"Data kunne ikke hentes: {e}")
            return

    df_events = st.session_state["events_data"].copy()

    # --- 3. FILTER-RÆKKE (OVER TABS) ---
    # Vi placerer dropdowns i toppen, så tabs får hele bredden nedenunder
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

    # --- 4. TABS (NU I FULD BREDDE) ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # FANEN: MED BOLD
    with tabs[1]:
        # Vi bruger 2 store kolonner for at få store billeder
        c1, c2 = st.columns(2)
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING (Egen halvdel)</p>', unsafe_allow_html=True)
            fig, ax = pitch.draw(figsize=(6, 8))
            ax.set_ylim(0, 50) # Mål nederst
            df_opbyg = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] < 50)]
            if not df_opbyg.empty:
                sns.kdeplot(x=df_opbyg['EVENT_Y'], y=df_opbyg['EVENT_X'], fill=True, cmap='Reds', 
                            alpha=0.6, levels=10, thresh=0.05, ax=ax, clip=((0, 100), (0, 50)))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        with c2:
            st.markdown('<p class="pitch-label">GENNEMBRUD (Modstander)</p>', unsafe_allow_html=True)
            fig, ax = pitch.draw(figsize=(6, 8))
            ax.set_ylim(50, 100) # Mål øverst
            df_gen = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] >= 50)]
            if not df_gen.empty:
                sns.kdeplot(x=df_gen['EVENT_Y'], y=df_gen['EVENT_X'], fill=True, cmap='Reds', 
                            alpha=0.6, levels=10, thresh=0.05, ax=ax, clip=((0, 100), (50, 100)))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    # FANEN: MOD BOLD
    with tabs[2]:
        # Her bruger vi en bredere midter-kolonne for at få en stor fuld bane
        _, mid_col, _ = st.columns([0.5, 3, 0.5])
        with mid_col:
            st.markdown('<p class="pitch-label">DEFENSIV INTENSITET (Dueller & Erobringer)</p>', unsafe_allow_html=True)
            pitch_full = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch_full.draw(figsize=(8, 11))
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
