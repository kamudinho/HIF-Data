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

    if df_team_matches is None or df_team_matches.empty:
        st.error("Kunne ikke finde kampdata.")
        return

    # --- 2. VALG AF MODSTANDER ---
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    valgt_navn = st.selectbox("Vælg modstander:", options=sorted(navne_dict.keys()))
    valgt_id = navne_dict[valgt_navn]
    
    # Forbered kamp-statistik (Begræns til de seneste 10 kampe for trendline)
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    df_f['DATE'] = pd.to_datetime(df_f['DATE']).dt.date
    df_f = df_f.sort_values('DATE', ascending=True)
    df_trend = df_f.tail(10) # Kun de seneste 10 kampe

    # --- 3. HOVEDLAYOUT ---
    main_left, main_right = st.columns([2, 1])

    with main_left:
        st.subheader(f"Positionsanalyse (Heatmaps): {valgt_navn}")
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#f8f9fa', line_color='#1a1a1a', linewidth=1)
        
        # 3 heatmaps ved siden af hinanden
        c1, c2, c3 = st.columns(3)

        if df_events is not None and not df_events.empty:
            # Tving kolonnenavne til upper
            df_events.columns = [c.upper() for c in df_events.columns]
            df_hold = df_events[df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))].copy()

            # 1. PASS HEATMAP
            with c1:
                st.caption("Afleveringer")
                fig, ax = pitch.draw(figsize=(4, 6))
                df_p = df_hold[df_hold['PRIMARYTYPE'].str.contains('pass', case=False, na=False)]
                if not df_p.empty:
                    sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], ax=ax, fill=True, cmap='Reds', alpha=0.6, clip=((0, 100), (0, 100)), levels=10)
                st.pyplot(fig)

            # 2. DUEL HEATMAP
            with c2:
                st.caption("Dueller")
                fig, ax = pitch.draw(figsize=(4, 6))
                df_d = df_hold[df_hold['PRIMARYTYPE'].str.contains('duel', case=False, na=False)]
                if not df_d.empty:
                    sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], ax=ax, fill=True, cmap='Blues', alpha=0.6, clip=((0, 100), (0, 100)), levels=10)
                st.pyplot(fig)

            # 3. INTERCEPTION HEATMAP
            with c3:
                st.caption("Interceptions")
                fig, ax = pitch.draw(figsize=(4, 6))
                df_i = df_hold[df_hold['PRIMARYTYPE'].str.contains('interception', case=False, na=False)]
                if not df_i.empty:
                    sns.kdeplot(x=df_i['LOCATIONY'], y=df_i['LOCATIONX'], ax=ax, fill=True, cmap='Greens', alpha=0.6, clip=((0, 100), (0, 100)), levels=10)
                st.pyplot(fig)

    # --- HØJRE SIDE: METRICS & TREND (KUN 10 KAMPE) ---
    with main_right:
        st.subheader("Form & Statistik")
        
        m_col1, m_col2 = st.columns(2)
        avg_xg = df_f['XG'].mean()
        
        with m_col1:
            st.metric("Gns. xG", round(avg_xg, 2))
        with m_col2:
            seneste_xg_mean = df_trend['XG'].mean()
            st.metric("Trend (10 kampe)", round(seneste_xg_mean, 2), delta=round(seneste_xg_mean - avg_xg, 2))

        st.markdown("---")
        st.write("**xG Udvikling (Seneste 10 kampe)**")
        # Grafen viser kun de seneste 10 rækker
        st.line_chart(df_trend.set_index('DATE')['XG'], color="#df003b")
        
        # Konvertering
        total_shots = df_f['SHOTS'].sum()
        total_goals = df_f['GOALS'].sum()
        if total_shots > 0:
            rate = (total_goals / total_shots) * 100
            st.write(f"**Mål/Skud Rate:** {round(rate, 1)}%")
            st.progress(min(rate/30, 1.0))

        st.info(f"**Scout Note:** De blå områder viser hvor {valgt_navn} søger duellerne, mens de røde viser deres opbygningszoner.")

    with st.expander("Se rå kampdata"):
        st.dataframe(df_f.sort_values('DATE', ascending=False), use_container_width=True)
