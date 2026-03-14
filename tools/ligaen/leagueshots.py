import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# Farver
HIF_RED = '#d71920'
LIGA_BLUE = '#1f77b4'

def vis_side(dp):
    # --- 1. DATA INDLÆSNING & LOGO SETUP ---
    opta_data = dp.get('opta', {})
    logo_map = dp.get("logo_map", {})
    df_skud = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_skud.empty:
        st.warning("Ingen liga-skuddata fundet.")
        return
    
    df_skud.columns = [c.upper() for c in df_skud.columns]
    col_team = 'EVENT_CONTESTANT_OPTAUUID'

    # --- 2. HJÆLPEFUNKTIONER ---
    def get_logo_url(opta_uuid):
        wy_id = next((info.get('team_wyid') for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
        if wy_id and wy_id in logo_map:
            return logo_map[wy_id]
        return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

    def get_logo_html(uuid):
        url = get_logo_url(uuid)
        # Vi sikrer at logoet har en fast højde så rækkerne flugter
        return f'<img src="{url}" height="22" style="vertical-align: middle;">' if url else ""

    # --- 3. DATABEREGNING ---
    df_skud['IS_DZ'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)
    
    stats_list = []
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    for p in df_skud['PLAYER_NAME'].unique():
        d = df_skud[df_skud['PLAYER_NAME'] == p]
        t_uuid = str(d[col_team].iloc[0]).upper()
        
        s = len(d)
        m = len(d[d['EVENT_TYPEID'] == 16])
        dz_d = d[d['IS_DZ'] == True]
        dz_s = len(dz_d)
        dz_m = len(dz_d[dz_d['EVENT_TYPEID'] == 16])
        
        if s > 0:
            stats_list.append({
                "UUID": t_uuid,
                "Spiller": p, 
                "Klub": uuid_to_name.get(t_uuid, "Modstander"), 
                "Skud": int(s),
                "Mål": int(m),
                "K%": float(round((m/s*100), 1)) if s > 0 else 0,
                "DZ-S": int(dz_s),
                "DZ-M": int(dz_m),
                "DZ-Andel": float(round((dz_s/s*100), 1)) if s > 0 else 0
            })
    
    # SORTERING PÅ MÅL (Top 20)
    df_final = pd.DataFrame(stats_list).sort_values("Mål", ascending=False).head(20).reset_index(drop=True)
    df_final.insert(0, '#', df_final.index + 1)

    # --- 4. LAYOUT & TABS ---
    tabs = st.tabs(["LIGAPROFILER (TOP 20)", "AFSLUTNINGER", "DZ-ANALYSE", "ZONER"])

    with tabs[0]:
        # CSS styling til den manuelle tabel
        st.markdown(f"""
            <style>
                .liga-table {{ width: 100%; border-collapse: collapse; color: #333; font-size: 14px; margin-top: 10px; }}
                .liga-table th {{ background-color: #f8f9fa; padding: 12px 8px; text-align: center; border-bottom: 2px solid #ddd; font-weight: bold; }}
                .liga-table td {{ padding: 10px 8px; border-bottom: 1px solid #eee; text-align: center; }}
                .liga-table td.left {{ text-align: left; }}
                .bar-container {{ background: #f0f0f0; border-radius: 3px; width: 60px; height: 10px; display: inline-block; margin-right: 5px; }}
                .bar-fill {{ background: {HIF_RED}; height: 100%; border-radius: 3px; }}
                .goal-cell {{ font-weight: 800; color: {HIF_RED}; font-size: 15px; }}
            </style>
        """, unsafe_allow_html=True)

        # Start tabellen
        html_code = '<table class="liga-table"><thead><tr>'
        html_code += '<th>#</th><th></th><th class="left">Spiller</th><th class="left">Klub</th><th>S</th><th>M</th><th>K%</th><th>DZ-S</th><th>DZ-Andel</th>'
        html_code += '</tr></thead><tbody>'

        for _, row in df_final.iterrows():
            logo = get_logo_html(row['UUID'])
            bar = f'<div class="bar-container"><div class="bar-fill" style="width: {row["DZ-Andel"]}%;"></div></div>'
            
            html_code += f"""
            <tr>
                <td>{row['#']}</td>
                <td>{logo}</td>
                <td class="left"><b>{row['Spiller']}</b></td>
                <td class="left" style="color: #666; font-size: 12px;">{row['Klub']}</td>
                <td>{row['Skud']}</td>
                <td class="goal-cell">{row['Mål']}</td>
                <td>{row['K%']}%</td>
                <td>{row['DZ-S']}</td>
                <td>{bar} <span style="font-size: 10px;">{row['DZ-Andel']}%</span></td>
            </tr>
            """
        
        html_code += '</tbody></table>'
        
        # DETTE ER DEN VIGTIGE LINJE:
        st.markdown(html_code, unsafe_allow_html=True)

    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            sel_p = st.selectbox("Vælg Spiller", sorted(df_skud['PLAYER_NAME'].unique()))
            d_v = df_skud[df_skud['PLAYER_NAME'] == sel_p]
            st.metric("Skud", len(d_v))
            st.metric("Mål", len(d_v[d_v["EVENT_TYPEID"]==16]))
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=100, c=colors, edgecolors=HIF_RED, ax=ax, alpha=0.8)
            st.pyplot(fig)
