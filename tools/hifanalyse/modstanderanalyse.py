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
    
    col_sel, col_halv, col_spiller = st.columns([1.5, 1, 1.5])
    with col_sel:
        valgt_hold = st.selectbox("Vælg modstander:", hold_liste, key="opp_team_sel")
    with col_halv:
        halvdel = st.radio("Fokus:", ["Offensiv", "Defensiv"], horizontal=True)
    
    hold_info = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]
    if hold_info.empty:
        st.warning("Ingen data fundet for det valgte hold.")
        return
    
    hold_uuid = hold_info['HOMECONTESTANT_OPTAUUID'].iloc[0]
    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy()

    with col_spiller:
        spiller_liste = ["Alle spillere"] + sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Filter spiller:", spiller_liste)

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    def map_type(tid):
        if tid == 1: return 'pass'
        if tid in [4, 5]: return 'duel'
        if tid in [8, 49]: return 'erobring'
        return 'other'
    df_hold['type'] = df_hold['EVENT_TYPEID'].apply(map_type)

    # --- 4. POSITIONERINGS-LOGIK (ALTID FREMADRETTET) ---
    if halvdel == "Offensiv":
        # Fra midten (50) mod modstanderens mål (100)
        df_plot = df_hold[df_hold['EVENT_X'] >= 50].copy()
    else:
        # Fra eget mål (0) mod midten (50)
        # Vi spejler X, så eget mål (0) vises øverst (100) i 'half=True' visningen
        df_plot = df_hold[df_hold['EVENT_X'] < 50].copy()
        df_plot['EVENT_X'] = 100 - df_plot['EVENT_X']
        # Vi spejler også Y, så venstre side forbliver venstre side i spilleretningen
        df_plot['EVENT_Y'] = 100 - df_plot['EVENT_Y']

    # --- 5. TABS ---
    tabs = st.tabs(["INTENSITET (HEATMAP)", "TOP PROFILER", "ZONE ANALYSE"])

    with tabs[0]:
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        cols = st.columns(3)
        kategorier = [
            ('pass', 'Afleveringer', 'Reds'),
            ('duel', 'Dueller', 'Blues'),
            ('erobring', 'Erobringer', 'Greens')
        ]

        for i, (kat_id, kat_navn, kat_cmap) in enumerate(kategorier):
            with cols[i]:
                st.markdown(f"<p style='text-align:center; font-weight:bold;'>{kat_navn}</p>", unsafe_allow_html=True)
                fig, ax = pitch.draw(figsize=(4, 6))
                df_subset = df_plot[df_plot['type'] == kat_id]

                if not df_subset.empty:
                    sns.kdeplot(
                        x=df_subset['EVENT_Y'], y=df_subset['EVENT_X'], 
                        fill=True, cmap=kat_cmap, alpha=0.6, 
                        levels=10, thresh=0.05, ax=ax, clip=((0, 100), (50, 100))
                    )
                else:
                    ax.text(50, 75, "Ingen hændelser", ha='center', color='gray')
                st.pyplot(fig)
                plt.close(fig)

    with tabs[1]:
        st.markdown(f"#### Statistisk overblik: {valgt_hold}")
        stat_cols = st.columns(3)
        for i, (kat_id, kat_navn, _) in enumerate(kategorier):
            with stat_cols[i]:
                top_spillere = df_plot[df_plot['type'] == kat_id]['PLAYER_NAME'].value_counts().head(8)
                st.markdown(f"**Top {kat_navn}**")
                for navn, count in top_spillere.items():
                    st.markdown(f'<div class="stat-box"><b>{count}</b> {navn}</div>', unsafe_allow_html=True)

    with tabs[2]:
        st.markdown("#### Zonefordeling")
        st.info(f"Oversigt over involveringer fordelt på banens zoner ({halvdel}).")
        
        # Opretter zoner baseret på den valgte halvdel (altid set i spilleretningen)
        df_plot['Afstand'] = pd.cut(df_plot['EVENT_X'], bins=[50, 65, 80, 100], labels=['Bagerst', 'Midt', 'Forrest'])
        df_plot['Side'] = pd.cut(df_plot['EVENT_Y'], bins=[0, 25, 75, 100], labels=['Venstre', 'Centrum', 'Højre'])
        
        zone_summary = df_plot.groupby(['Afstand', 'Side']).size().unstack().fillna(0)
        st.table(zone_summary)

if __name__ == "__main__":
    vis_side()
