import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import matplotlib.patches as patches

def vis_side(analysis_package):
    # --- 1. CSS & STYLING (Ensartet med resten af appen) ---
    st.markdown("""
        <style>
            .stTabs { margin-top: -30px; }
            .stat-box { 
                background-color: #f8f9fa; 
                padding: 10px; 
                border-radius: 8px; 
                border-left: 5px solid #df003b; 
                margin-bottom: 10px; 
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA-LOAD ---
    if "events_data" not in st.session_state:
        # (Din eksisterende Snowflake-load logik her...)
        # For eksemplets skyld antager vi df_events er klar:
        st.warning("Data ikke fundet i session_state. Indlæser...")
        return

    df_events = st.session_state["events_data"].copy()

    # --- 3. UNIVERSAL FILTRERING (Top-bar) ---
    hold_liste = sorted(df_events['HOMECONTESTANT_NAME'].unique())
    
    col_sel, col_halv, col_spiller = st.columns([1.5, 1, 1.5])
    with col_sel:
        valgt_hold = st.selectbox("Vælg modstander:", hold_liste, key="opp_team_sel")
    with col_halv:
        halvdel = st.radio("Fokus:", ["Offensiv", "Defensiv"], horizontal=True)
    
    # Filtrer data for det valgte hold
    hold_uuid = df_events[df_events['HOMECONTESTANT_NAME'] == valgt_hold]['HOMECONTESTANT_OPTAUUID'].iloc[0]
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

    # Spejling
    if halvdel == "Offensiv":
        df_plot = df_hold[df_hold['EVENT_X'] >= 50].copy()
    else:
        df_plot = df_hold[df_hold['EVENT_X'] < 50].copy()
        df_plot['EVENT_X'] = 100 - df_plot['EVENT_X'] # Spejl til toppen af banen

    # --- 4. VISUALISERING ---
    tabs = st.tabs(["INTENSITET (HEATMAP)", "TOP PRESTATIONER", "ZONE ANALYSE"])

    with tabs[0]:
        pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        cols = st.columns(3)
        kategorier = [
            ('pass', 'Afleveringer', 'Reds'),
            ('duel', 'Vundne Dueller', 'Blues'),
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
                    ax.text(50, 75, "Ingen data", ha='center', color='gray')
                st.pyplot(fig)
                plt.close(fig)

    with tabs[1]:
        st.markdown(f"### Top 5 profiler - {valgt_hold} ({halvdel})")
        stat_cols = st.columns(3)
        for i, (kat_id, kat_navn, _) in enumerate(kategorier):
            with stat_cols[i]:
                top_spillere = df_plot[df_plot['type'] == kat_id]['PLAYER_NAME'].value_counts().head(5)
                st.markdown(f"**{kat_navn}**")
                if not top_spillere.empty:
                    for navn, count in top_spillere.items():
                        st.markdown(f"""
                        <div class="stat-box">
                            <span style="font-weight:bold; color:#df003b;">{count}</span> {navn}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.write("Ingen data")

    with tabs[2]:
        st.info("Her kan vi indsætte tabeller med specifikke zone-gennembrud eller boldtab i farlige områder.")
