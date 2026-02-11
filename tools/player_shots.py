import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mplsoccer import VerticalPitch

def vis_side(df_events, df_spillere, hold_map):
    HIF_ID = 38331
    HIF_RED = '#d31313'

    # --- 0. CSS TIL OPTIMERING ---
    st.markdown("""
        <style>
            .main .block-container { padding-bottom: 1rem; padding-top: 2rem; }
            footer {display: none;}
            div[data-testid="stSelectbox"] { margin-bottom: -10px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. DATA-PROCESSERING ---
    s_df = df_spillere.copy()
    s_df.columns = [str(c).strip().upper() for c in s_df.columns]
    
    s_df['FULL_NAME'] = s_df.apply(
        lambda x: f"{x.get('FIRSTNAME', '')} {x.get('LASTNAME', '')}".strip() 
        if pd.notna(x.get('FIRSTNAME')) or pd.notna(x.get('LASTNAME')) 
        else x.get('NAVN', "-"), axis=1
    )
    
    s_df['PLAYER_WYID'] = s_df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()
    navne_dict = dict(zip(s_df['PLAYER_WYID'], s_df['FULL_NAME']))

    df = df_events.copy()
    df.columns = [str(c).strip().upper() for c in df.columns]
    df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.split('.').str[0].str.strip()

    # Filtrering (Kun skud fra HIF)
    mask = df['PRIMARYTYPE'].str.contains('shot', case=False, na=False)
    if 'TEAM_WYID' in df.columns:
        mask &= (df['TEAM_WYID'].astype(float).astype(int) == HIF_ID)
    
    df_s = df[mask].copy()
    
    # Sørg for numeriske værdier
    for col in ['LOCATIONX', 'LOCATIONY', 'SHOTXG', 'MINUTE']:
        if col in df_s.columns:
            df_s[col] = pd.to_numeric(df_s[col], errors='coerce')

    if df_s.empty:
        st.info("Ingen afslutninger fundet.")
        return

    df_s['MODSTANDER'] = df_s['OPPONENTTEAM_WYID'].apply(lambda x: hold_map.get(int(float(x)), f"Hold {x}") if pd.notna(x) else "Ukendt")
    df_s = df_s.sort_values(by=['MODSTANDER', 'MINUTE']).reset_index(drop=True)
    df_s['SHOT_NR'] = df_s.index + 1
    df_s['SPILLER_NAVN'] = df_s['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 2. LAYOUT ---
    layout_venstre, layout_hoejre = st.columns([2, 1])

    with layout_hoejre:
        st.write("##") 
        
        spiller_liste = sorted(df_s['SPILLER_NAVN'].unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller", ["Alle Spillere"] + spiller_liste, label_visibility="collapsed")
        
        # DEFINER df_plot HER (Det er her fejlen lå)
        df_plot = (df_s if valgt_spiller == "Alle Spillere" else df_s[df_s['SPILLER_NAVN'] == valgt_spiller]).copy()
        er_alle = valgt_spiller == "Alle Spillere"

        with st.popover("Dataoverblik", use_container_width=True):
            tabel_df = df_plot.copy()
            if 'SHOTISGOAL' in tabel_df.columns:
                tabel_df['RESULTAT'] = tabel_df['SHOTISGOAL'].apply(lambda x: "MÅL" if str(x).lower() in ['true', '1', '1.0'] else "Skud")
            else:
                tabel_df['RESULTAT'] = "Skud"
                
            vis_tabel = tabel_df[['SHOT_NR', 'MODSTANDER', 'MINUTE', 'SPILLER_NAVN', 'RESULTAT']]
            vis_tabel.columns = ['Nr.', 'Modstander', 'Minut', 'Spiller', 'Resultat']
            st.dataframe(vis_tabel, hide_index=True, use_container_width=True)

        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

        # Metrics beregninger
        def get_stat_sum(dataframe, col_name):
            if col_name in dataframe.columns:
                return int(dataframe[col_name].fillna(False).map({'true': True, 'false': False, True: True, False: False, 1: True, 0: False, 1.0: True, 0.0: False}).sum())
            return 0

        SHOTS = len(df_plot)
        GOALS = get_stat_sum(df_plot, 'SHOTISGOAL')
        ON_TARGET = get_stat_sum(df_plot, 'SHOTONTARGET')
        XG_TOTAL = df_plot['SHOTXG'].sum() if 'SHOTXG' in df_plot.columns else 0.0
        AVG_DIST = (100 - df_plot['LOCATIONX']).mean() if not df_plot.empty else 0

        def custom_metric(label, value):
            st.markdown(f"""
                <div style="margin-bottom: 12px; border-left: 2px solid {HIF_RED}; padding-left: 12px;">
                    <p style="margin:0; font-size: 12px; color: #777; text-transform: uppercase;">{label}</p>
                    <p style="margin:0; font-size: 26px; font-weight: 700; color: #222;">{value}</p>
                </div>
            """, unsafe_allow_html=True)

        custom_metric("Afslutninger", SHOTS)
        custom_metric("Mål", GOALS)
        custom_metric("Konverteringsrate", f"{(GOALS / SHOTS * 100) if SHOTS > 0 else 0:.1f}%")
        custom_metric("Skud på mål", ON_TARGET)
        custom_metric("Expected Goals (xG)", f"{XG_TOTAL:.2f}")
        custom_metric("Gns. Afstand", f"{AVG_DIST:.1f} m")

    with layout_venstre:
        # Bane-setup
        pitch = VerticalPitch(half=True, pitch_type='wyscout', line_color='#444444', line_zorder=2, pad_bottom=0)
        fig, ax = pitch.draw(figsize=(6, 5))
        ax.set_ylim(45, 102) 

        # Nu virker loopet fordi df_plot er defineret ovenfor
        for _, row in df_plot.iterrows():
            val = str(row.get('SHOTISGOAL', 'false')).lower()
            is_goal = val in ['true', '1', '1.0']
            
            ax.scatter(row['LOCATIONY'], row['LOCATIONX'], 
                       s=200 if is_goal else 110,
                       color=HIF_RED, edgecolors='white', linewidth=1.2 if is_goal else 0.5, 
                       alpha=0.7 if er_alle else 0.9, zorder=3)
            
            if not er_alle:
                ax.text(row['LOCATIONY'], row['LOCATIONX'], str(int(row['SHOT_NR'])), 
                        color='white', ha='center', va='center', fontsize=6, fontweight='bold', zorder=4)
        
        st.pyplot(fig, bbox_inches='tight', pad_inches=0.05)
