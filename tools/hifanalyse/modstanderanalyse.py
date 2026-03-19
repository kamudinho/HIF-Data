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
                font-size: 0.9rem;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA-LOAD ---
    if "events_data" not in st.session_state:
        with st.spinner("Henter modstander-data fra Snowflake..."):
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
                df_res = conn.query(query)
                st.session_state["events_data"] = pd.DataFrame(df_res)
            except Exception as e:
                st.error(f"Fejl ved data-hentning: {e}")
                return

    df_events = st.session_state["events_data"].copy()

    # --- 3. FILTRERING ---
    hold_liste = sorted(df_events['HOMECONTESTANT_NAME'].unique())
    
    col_sel, col_fase, col_spiller = st.columns([1.5, 1.2, 1.3])
    with col_sel:
        valgt_hold = st.selectbox("Vælg hold:", hold_liste, key="opp_team_sel")
    with col_fase:
        fase = st.radio("Spilfase:", ["Med bold", "Mod bold"], horizontal=True)
    
    hold_info = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]
    if hold_info.empty:
        st.warning("Ingen data fundet.")
        return
    
    hold_uuid = hold_info['HOMECONTESTANT_OPTAUUID'].iloc[0]
    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()

    with col_spiller:
        spiller_liste = ["Alle spillere"] + sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Filter spiller:", spiller_liste)

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    # Mapping af typer
    def map_type(tid):
        if tid == 1: return 'pass'
        if tid in [4, 5]: return 'duel'
        if tid in [8, 49]: return 'erobring'
        return 'other'
    df_hold['type'] = df_hold['EVENT_TYPEID'].apply(map_type)

    # --- 4. FASE-LOGIK ---
    is_half = True
    if fase == "Med bold":
        sub_fase = st.segmented_control("Område:", ["Opbygning (Egen)", "Gennembrud (Modstander)"], default="Gennembrud (Modstander)")
        
        if sub_fase == "Opbygning (Egen)":
            # Egen halvdel (0-50). Vi gør 0 til bund og 50 til top.
            df_plot = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] < 50)].copy()
            # Ved VerticalPitch er bunden 0 og toppen 100. Så vi behøver ikke spejle X her, 
            # hvis vi bare viser den nederste halvdel.
            is_half_bottom = True 
        else:
            # Modstanders halvdel (50-100).
            df_plot = df_hold[(df_hold['type'] == 'pass') & (df_hold['EVENT_X'] >= 50)].copy()
            is_half_bottom = False
    else:
        # Mod bold: Fuld bane, kun dueller og erobringer
        df_plot = df_hold[df_hold['type'].isin(['duel', 'erobring'])].copy()
        is_half = False

    # --- 5. VISUALISERING ---
    tabs = st.tabs(["INTENSITET (HEATMAP)", "TOP PROFILER"])

    with tabs[0]:
        # Konfigurer banevisning
        if is_half:
            pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
            # Hvis vi er i opbygning, skal vi justere synsfeltet til 0-50
            if fase == "Med bold" and sub_fase == "Opbygning (Egen)":
                # Vi bruger stadig VerticalPitch(half=True), men vi fortæller ax at den skal vise 0-50
                ylim_pitch = (0, 50)
            else:
                ylim_pitch = (50, 100)
        else:
            pitch = VerticalPitch(pitch_type='opta', half=False, pitch_color='#ffffff', line_color='#333333')
            ylim_pitch = (0, 100)

        cols = st.columns(3)
        # Relevante kategorier baseret på fase
        if fase == "Med bold":
            kategorier = [('pass', 'Afleveringer', 'Reds')]
        else:
            kategorier = [('duel', 'Dueller', 'Blues'), ('erobring', 'Erobringer', 'Greens')]

        for i, (kat_id, kat_navn, kat_cmap) in enumerate(kategorier):
            with cols[i if fase == "Mod bold" else 1]: # Centrer hvis kun én
                st.markdown(f"<p style='text-align:center; font-weight:bold;'>{kat_navn}</p>", unsafe_allow_html=True)
                fig, ax = pitch.draw(figsize=(4, 6))
                ax.set_ylim(ylim_pitch) # Her styres hvilken halvdel der ses
                
                df_subset = df_plot[df_plot['type'] == kat_id]
                if not df_subset.empty:
                    sns.kdeplot(
                        x=df_subset['EVENT_Y'], y=df_subset['EVENT_X'], 
                        fill=True, cmap=kat_cmap, alpha=0.6, 
                        levels=10, thresh=0.05, ax=ax
                    )
                else:
                    ax.text(50, (ylim_pitch[0]+ylim_pitch[1])/2, "Ingen data", ha='center', color='gray')
                st.pyplot(fig)
                plt.close(fig)

    with tabs[1]:
        st.markdown(f"#### Statistisk overblik: {valgt_hold}")
        stat_cols = st.columns(len(kategorier))
        for i, (kat_id, kat_navn, _) in enumerate(kategorier):
            with stat_cols[i]:
                top_spillere = df_plot[df_plot['type'] == kat_id]['PLAYER_NAME'].value_counts().head(10)
                st.markdown(f"**Top {kat_navn}**")
                for navn, count in top_spillere.items():
                    st.markdown(f'<div class="stat-box"><b>{count}</b> {navn}</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
