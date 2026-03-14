import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# --- DESIGN KONSTANTER ---
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    # 1. DATA & LOGO SETUP
    opta_data = dp.get('opta', {})
    logo_map = dp.get("logo_map", {})
    df_skud = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_skud.empty:
        st.info("Ingen data fundet.")
        return
    
    df_skud.columns = [c.upper() for c in df_skud.columns]
    col_team_uuid = 'EVENT_CONTESTANT_OPTAUUID'
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}

    # 2. CSS STYLING
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {HIF_RED}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; }}
            .stat-value {{ font-size: 1.4rem; font-weight: 800; color: #1a1a1a; }}
            .hif-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
            .hif-table th {{ background: #eee; padding: 8px; text-align: center; border-bottom: 2px solid #ccc; }}
            .hif-table td {{ padding: 8px; border-bottom: 1px solid #eee; text-align: center; vertical-align: middle; }}
            .hif-table td.left {{ text-align: left; }}
        </style>
    """, unsafe_allow_html=True)

    # 3. TABS
    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-ANALYSE", "ZONER"])

    # --- TAB 0: SPILLEROVERSIGT (Klub tekst fjernet, logo beholdt) ---
    with tabs[0]:
        stats = []
        for p in df_skud['PLAYER_NAME'].unique():
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            t_uuid = str(d[col_team_uuid].iloc[0]).upper()
            dz = d[(d['EVENT_X'] >= 88.5) & (d['EVENT_Y'] >= 37.0) & (d['EVENT_Y'] <= 63.0)]
            
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            xg = d['EXPECTED_GOALS_VALUE'].sum() if 'EXPECTED_GOALS_VALUE' in d.columns else 0
            
            stats.append({
                "UUID": t_uuid, "Spiller": p, "S": s, "M": m, 
                "xG": round(xg, 2), "K%": round((m/s*100),1) if s > 0 else 0,
                "DZ-S": len(dz), "DZ-M": len(dz[dz['EVENT_TYPEID'] == 16]),
                "DZ-%": round((len(dz)/s*100),0) if s > 0 else 0
            })
        
        df_f = pd.DataFrame(stats).sort_values("M", ascending=False).head(20).reset_index(drop=True)
        
        html = '<table class="hif-table"><thead><tr><th>#</th><th></th><th class="left">Spiller</th><th>S</th><th>M</th><th>xG</th><th>K%</th><th>DZ-S</th><th>DZ-M</th><th>DZ-Andel</th></tr></thead><tbody>'
        for i, row in df_f.iterrows():
            wy_id = next((v['team_wyid'] for k, v in TEAMS.items() if v.get('opta_uuid') == row['UUID']), None)
            l_url = logo_map.get(wy_id, "")
            img = f'<img src="{l_url}" width="25">' if l_url else ""
            
            html += f"""<tr>
                <td>{i+1}</td><td>{img}</td><td class="left"><b>{row['Spiller']}</b></td>
                <td>{row['S']}</td><td style="color:{HIF_RED}; font-weight:bold;">{row['M']}</td>
                <td>{row['xG']}</td><td>{row['K%']}%</td><td>{row['DZ-S']}</td><td>{row['DZ-M']}</td>
                <td><div style="background:#eee; width:40px; height:8px; display:inline-block;"><div style="background:{HIF_RED}; width:{row['DZ-%']}%; height:100%;"></div></div> {int(row['DZ-%'])}%</td>
            </tr>"""
        st.markdown(html + "</tbody></table>", unsafe_allow_html=True)

    # --- DYNAMISK FILTRERING FUNKTION ---
    def get_smart_filters(suffix):
        uuids = df_skud[col_team_uuid].unique()
        available_teams = sorted([uuid_to_name[u.upper()] for u in uuids if u.upper() in uuid_to_name])
        
        # Vi placerer dropdowns øverst i kontrol-kolonnen
        st.markdown("### Filter")
        sel_team = st.selectbox("Hold", ["ALLE HOLD"] + available_teams, key=f"t_{suffix}")
        
        if sel_team == "ALLE HOLD":
            p_list = sorted(df_skud['PLAYER_NAME'].unique())
            d_out = df_skud
        else:
            t_uuid = next(v['opta_uuid'].upper() for k, v in TEAMS.items() if k == sel_team)
            d_out = df_skud[df_skud[col_team_uuid].str.upper() == t_uuid]
            p_list = sorted(d_out['PLAYER_NAME'].unique())
            
        sel_p = st.selectbox("Spiller", ["HELE HOLDET"] + p_list, key=f"p_{suffix}")
        return d_out[d_out['PLAYER_NAME'] == sel_p] if sel_p != "HELE HOLDET" else d_out

    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            d_v = get_smart_filters("afsl")
            s, m = len(d_v), len(d_v[d_v["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=(d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'}), edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: DZ-ANALYSE (ZOOMET IND) ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2:
            d_v = get_smart_filters("dz")
            dz_d = d_v[(d_v['EVENT_X'] >= 88.5) & (d_v['EVENT_Y'] >= 37.0) & (d_v['EVENT_Y'] <= 63.0)]
            st.markdown(f'<div class="stat-box" style="border-left-color:{DZ_COLOR}"><div class="stat-label">DZ Skud</div><div class="stat-value">{len(dz_d)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{DZ_COLOR}"><div class="stat-label">DZ Mål</div><div class="stat-value">{len(dz_d[dz_d["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            # AFKORTNING: Vi sætter Y-grænsen til feltkanten/cirklen (ca. 75-105)
            ax.set_ylim(75, 105) 
            ax.set_xlim(10, 90) # Bevarer bredden, men zoomer lidt ind
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=120, c=(dz_d['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'}), edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- TAB 3: ZONER ---
    with tabs[3]:
        c1, c2 = st.columns([2, 1])
        with c2:
            d_v = get_smart_filters("zone")
            st.write("Zonefordeling kommer her...")
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            st.pyplot(fig)

# For at køre: vis_side(data_provider)
