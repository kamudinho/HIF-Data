import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'

    # --- 0. CSS TIL OPTIMERING AF PLADS ---
    st.markdown("""
        <style>
            /* Fjerner hvid plads i bunden og Streamlit footer */
            .main .block-container {
                padding-bottom: 1rem;
            }
            footer {display: none;}
            /* Gør selectbox og popover mere kompakte */
            div[data-testid="stSelectbox"] { margin-bottom: -10px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. DATA-PROCESSERING ---
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    
    s_df['FULL_NAME'] = s_df.apply(
        lambda x: f"{x.get('FIRSTNAME', '')} {x.get('LASTNAME', '')}".strip() if pd.notna(x.get('FIRSTNAME')) or pd.notna(x.get('LASTNAME')) else x.get('NAVN', "-"),
        axis=1
    )
    
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['FULL_NAME']))

    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if 'TEAM_WYID' in df.columns:
        mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_s = df[mask].copy()
    df_s['LOCATIONX'] = pd.to_numeric(df_s['LOCATIONX'], errors='coerce')
    df_s['LOCATIONY'] = pd.to_numeric(df_s['LOCATIONY'], errors='coerce')
    df_s = df_s.dropna(subset=['LOCATIONX', 'LOCATIONY'])

    if df_s.empty:
        st.info("Ingen afslutninger fundet.")
        return

    df_s['MODSTANDER'] = df_s['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(x), f"Hold {x}") if pd.notna(x) else "Ukendt")
    df_s = df_s.sort_values(by=['MODSTANDER', 'MINUTE']).reset_index(drop=True)
    df_s['SHOT_NR'] = df_s.index + 1
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 2. LAYOUT ---
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        # Spacer for at få dropdown til at flugte med banen (justeret til ##)
        st.write("##") 
        
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste, label_visibility="collapsed")
        
        df_stats = (df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller]).copy()
        
        with st.popover("Dataoverblik", use_container_width=True):
            tabel_df = df_stats.copy()
            tabel_df['RESULTAT'] = tabel_df['PRIMARYTYPE'].apply(lambda x: "MÅL" if 'goal' in str(x).lower() else "Skud")
            vis_tabel = tabel_df[['SHOT_NR', 'MODSTANDER', 'MINUTE', 'SPILLER_NAVN', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Modstander', 'Minut', 'Spiller', 'Resultat']
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)

        st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

        # --- BEREGNING AF 6 METRICS ---
        SHOTS = len(df_stats)
        GOALS = len(df_stats[df_stats['PRIMARYTYPE'].str.contains('goal', case=False, na=False)])
        KONV = (GOALS / SHOTS * 100) if SHOTS > 0 else 0
        
        ON_TARGET = len(df_stats[df_stats['SECONDARYTYPE'].str.contains('on_target', case=False, na=False)]) if 'SECONDARYTYPE' in df_stats.columns else GOALS
        XG_TOTAL = df_stats['XG'].sum() if 'XG' in df_stats.columns else 0.0
        AVG_DIST = (100 - df_stats['LOCATIONX']).mean() if not df_stats.empty else 0

        def custom_metric(label, value):
            st.markdown(f"""
                <div style="margin-bottom: 16px; border-left: 2px solid {HIF_RED}; padding-left: 12px;">
                    <p style="margin:0; font-size: 16px; color: #777; text-transform: uppercase; letter-spacing: 0.5px;">{label}</p>
                    <p style="margin:0; font-size: 26px; font-weight: 700; color: #222;">{value}</p>
                </div>
            """, unsafe_allow_html=True)

        custom_metric("Afslutninger", SHOTS)
        custom_metric("Mål", GOALS)
        custom_metric("Konverteringsrate", f"{KONV:.1f}%")
        custom_metric("Skud på mål", ON_TARGET)
        custom_metric("Expected Goals (xG)", f"{XG_TOTAL:.2f}")
        custom_metric("Gns. Afstand", f"{AVG_DIST:.1f} m")

    with layout_venstre:
        df_plot = df_stats.copy()
        er_alle = valgt_spiller == "Alle Spillere"

        if not df_plot.empty:
            jitter_val = 0.8 if er_alle else 0.5
            df_plot['LOC_X_JITTER'] = df_plot['LOCATIONX'] + np.random.uniform(-jitter_val, jitter_val, len(df_plot))
            df_plot['LOC_Y_JITTER'] = df_plot['LOCATIONY'] + np.random.uniform(-jitter_val, jitter_val, len(df_plot))

        # --- 4. TEGN BANE (Med optimerede marginer) ---
        pitch = VerticalPitch(
            half=True, 
            pitch_type='wyscout', 
            line_color='#444444', 
            line_zorder=2, 
            pad_bottom=-4, # Fjerner luft i bunden
            pad_top=1
        )
        
        fig, ax = pitch.draw(figsize=(6, 5))
        ax.set_ylim(45, 102) 

        for _, row in df_plot.iterrows():
            is_goal = 'goal' in str(row['PRIMARYTYPE']).lower()
            ax.scatter(row['LOC_Y_JITTER'], row['LOC_X_JITTER'], 
                       s=150 if is_goal else 80 if er_alle else 80,
                       color=HIF_RED, edgecolors='white', linewidth=1.2 if is_goal else 0.6, 
                       alpha=0.6 if er_alle else 0.9, zorder=3)
            if not er_alle:
                ax.text(row['LOC_Y_JITTER'], row['LOC_X_JITTER'], str(int(row['SHOT_NR'])), 
                        color='white', ha='center', va='center', fontsize=4, fontweight='bold', zorder=5)
        
        # Bruger bbox_inches='tight' for at fjerne hvid ramme om figuren
        st.pyplot(fig, bbox_inches='tight', pad_inches=0.05)
