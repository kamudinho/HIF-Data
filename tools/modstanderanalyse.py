import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_team_matches, hold_map, df_events):
    # --- 1. CSS STYLING ---
    st.markdown("""
        <style>
        .stMetric { 
            background-color: #ffffff; 
            padding: 10px; 
            border-radius: 8px; 
            border-bottom: 3px solid #df003b; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        }
        [data-testid="stMetricValue"] { font-size: 22px !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. VALG AF MODSTANDER & DATA ---
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    valgt_navn = st.selectbox("Vælg modstander:", options=sorted(navne_dict.keys()))
    valgt_id = navne_dict[valgt_navn]
    
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    df_f['DATE'] = pd.to_datetime(df_f['DATE']).dt.date
    df_f = df_f.sort_values('DATE', ascending=True) # Ascending til grafen

    # --- 3. HOVEDLAYOUT (BANER VS STATS) ---
    # Vi deler siden i to hovedkolonner: Baner (Venstre) og Stats/Trend (Højre)
    main_left, main_right = st.columns([1.8, 1])

    # --- VENSTRE SIDE: 2x2 BANER ---
    with main_left:
        st.subheader(f"Taktisk Analyse: {valgt_navn}")
        
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#f8f9fa', line_color='#1a1a1a', linewidth=1)
        
        # Opret 2 rækker med 2 kolonner
        r1_c1, r1_c2 = st.columns(2)
        r2_c1, r2_c2 = st.columns(2)

        if df_events is not None and not df_events.empty:
            df_hold = df_events[df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))].copy()
            match_ids = df_hold['MATCH_WYID'].unique() if 'MATCH_WYID' in df_events.columns else []
            df_opp = df_events[(df_events['MATCH_WYID'].isin(match_ids)) & (df_events['TEAM_WYID'].astype(str) != str(int(valgt_id)))]

            # BANE 1: AFLEVERINGER
            with r1_c1:
                st.caption("Afleveringsmønstre")
                fig, ax = pitch.draw(figsize=(4, 5))
                df_p = df_hold[df_hold['PRIMARYTYPE'].str.contains('pass', case=False, na=False)].tail(40)
                if not df_p.empty and 'ENDLOCATIONX' in df_p.columns:
                    pitch.arrows(df_p['LOCATIONX'], df_p['LOCATIONY'], df_p['ENDLOCATIONX'], df_p['ENDLOCATIONY'], width=1, color='#df003b', ax=ax)
                st.pyplot(fig)

            # BANE 2: EGEN SKUD
            with r1_c2:
                st.caption("Afslutninger (For)")
                fig, ax = pitch.draw(figsize=(4, 5))
                df_s = df_hold[df_hold['PRIMARYTYPE'].str.contains('shot', case=False, na=False)]
                pitch.scatter(df_s['LOCATIONX'], df_s['LOCATIONY'], s=40, color='#df003b', edgecolors='black', ax=ax)
                st.pyplot(fig)

            # BANE 3: SKUD IMOD
            with r2_c1:
                st.caption("Afslutninger (Imod)")
                fig, ax = pitch.draw(figsize=(4, 5))
                df_si = df_opp[df_opp['PRIMARYTYPE'].str.contains('shot', case=False, na=False)]
                pitch.scatter(df_si['LOCATIONX'], df_si['LOCATIONY'], s=40, color='blue', edgecolors='black', ax=ax)
                st.pyplot(fig)

            # BANE 4: DUELLER / HEATMAP
            with r2_c2:
                st.caption("Aktivitetszoner")
                fig, ax = pitch.draw(figsize=(4, 5))
                sns.kdeplot(x=df_hold['LOCATIONY'], y=df_hold['LOCATIONX'], ax=ax, fill=True, cmap='Reds', alpha=0.5, clip=((0, 100), (0, 100)))
                st.pyplot(fig)

    # --- HØJRE SIDE: METRICS & UDVIKLING ---
    with main_right:
        st.subheader("Performance & Trend")
        
        # Metrics i et 3x2 grid (3 rækker, 2 kolonner)
        m_col1, m_col2 = st.columns(2)
        
        avg_xg = df_f['XG'].mean()
        avg_poss = df_f['POSSESSIONPERCENT'].mean()
        avg_goals = df_f['GOALS'].mean()
        
        with m_col1:
            st.metric("Gns. xG", round(avg_xg, 2))
            st.metric("Gns. Mål", round(avg_goals, 1))
        with m_col2:
            st.metric("Possession", f"{round(avg_poss, 0)}%")
            # Trend delta beregning
            seneste_xg = df_f['XG'].tail(3).mean()
            st.metric("Trend (xG)", round(seneste_xg, 2), delta=round(seneste_xg - avg_xg, 2))

        st.markdown("---")
        
        # UDVIKLING I SAMME LINJE (Line chart)
        st.write("**xG Udvikling (Sæson)**")
        st.line_chart(df_f.set_index('DATE')['XG'], color="#df003b")
        
        # KONVERTERING
        total_shots = df_f['SHOTS'].sum()
        total_goals = df_f['GOALS'].sum()
        if total_shots > 0:
            rate = (total_goals / total_shots) * 100
            st.write(f"**Konverteringsrate:** {round(rate, 1)}%")
            st.progress(min(rate/30, 1.0))

        st.info(f"**Analytiker:** {valgt_navn} har en trend-score på {round(seneste_xg - avg_xg, 2)} over de sidste 3 kampe.")

    # --- 6. RÅ DATA ---
    with st.expander("Se kampdata"):
        st.dataframe(df_f.sort_values('DATE', ascending=False), use_container_width=True)
