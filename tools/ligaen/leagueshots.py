import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# Konstanter til farver (Hvidovre/Liga rød nuance til bars)
HIF_RED = '#d71920' 
LIGA_BLUE = '#1f77b4'

def vis_side(dp):
    # --- 1. DATA INDLÆSNING ---
    opta_data = dp.get('opta', {})
    df_skud = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_skud.empty:
        st.warning("Ingen liga-skuddata fundet.")
        return
    
    df_skud.columns = [c.upper() for c in df_skud.columns]
    col_team = 'EVENT_CONTESTANT_OPTAUUID'

    # --- 2. CSS STYLING ---
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {LIGA_BLUE}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 3. ZONE LOGIK (DZ DEFINITION) ---
    # Danger Zone: Centralt i feltet
    df_skud['IS_DZ'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    # --- 4. TABS ---
    tabs = st.tabs(["LIGAPROFILER", "AFSLUTNINGER", "DZ-ANALYSE", "SKUDZONER", "MÅLZONER"])

    with tabs[0]:
        stats_list = []
        uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
        
        for p in df_skud['PLAYER_NAME'].unique():
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            t_uuid = str(d[col_team].iloc[0]).upper()
            t_name = uuid_to_name.get(t_uuid, "Modstander")
            
            # Generelle stats
            s = len(d)
            m = len(d[d['EVENT_TYPEID'] == 16])
            
            # DZ stats
            dz_d = d[d['IS_DZ'] == True]
            dz_s = len(dz_d)
            dz_m = len(dz_d[dz_d['EVENT_TYPEID'] == 16])
            
            if s > 0:
                stats_list.append({
                    "Spiller": p, 
                    "Klub": t_name, 
                    "Skud": int(s),
                    "Mål": int(m),
                    "Konvertering%": float(round((m/s*100), 1)),
                    "DZ-Skud": int(dz_s),
                    "DZ-Mål": int(dz_m),
                    "DZ-Konvertering%": float(round((dz_m/dz_s*100), 1)) if dz_s > 0 else 0.0,
                    "DZ-Andel": float(round((dz_s/s*100), 1))
                })
        
        df_final = pd.DataFrame(stats_list).sort_values("Skud", ascending=False)
        
        # Visning præcis som på billedet
        st.dataframe(
            df_final, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Spiller": st.column_config.TextColumn("Spiller"),
                "Klub": st.column_config.TextColumn("Klub"),
                "Skud": st.column_config.NumberColumn("Skud", format="%d"),
                "Mål": st.column_config.NumberColumn("Mål", format="%d"),
                "Konvertering%": st.column_config.NumberColumn("Konvertering%", format="%.1f%%"),
                "DZ-Skud": st.column_config.NumberColumn("DZ-Skud", format="%d"),
                "DZ-Mål": st.column_config.NumberColumn("DZ-Mål", format="%d"),
                "DZ-Konvertering%": st.column_config.NumberColumn("DZ-Konvertering%", format="%.1f%%"),
                "DZ-Andel": st.column_config.ProgressColumn(
                    "DZ-Andel", 
                    format="%.0f%%", 
                    min_value=0, 
                    max_value=100,
                    color=HIF_RED # Rød bar som på billedet
                )
            }
        )

    # --- RESTEN AF FANERNE (Beholdes som de var) ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            sel_p = st.selectbox("Vælg Spiller", ["HELE LIGAEN"] + sorted(df_skud['PLAYER_NAME'].unique()))
            d_v = df_skud if sel_p == "HELE LIGAEN" else df_skud[df_skud['PLAYER_NAME'] == sel_p]
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(d_v)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(d_v[d_v["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=colors, edgecolors=HIF_RED, ax=ax, alpha=0.7)
            st.pyplot(fig)

    with tabs[2]:
        st.subheader("Danger Zone (DZ) Lokationer")
        st.write("Viser alle skud fra ligaen i det centrale område.")
        pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(8, 10))
        dz_only = df_skud[df_skud['IS_DZ']]
        pitch.scatter(dz_only['EVENT_X'], dz_only['EVENT_Y'], s=30, c=HIF_RED, alpha=0.3, ax=ax)
        st.pyplot(fig)
