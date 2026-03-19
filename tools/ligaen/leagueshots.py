import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from PIL import Image
import requests
from io import BytesIO

# HIF Design & Standarder
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
DZ_COLOR = '#1f77b4'

# --- UTILS: FARVER, LOGOER & KONTRAST ---

@st.cache_data(ttl=3600)
def get_logo_img(url):
    """Henter og cacher holdlogo."""
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except:
        return None

def get_text_color(hex_color):
    """Beregner om tekst skal være sort eller hvid baseret på baggrundens lysstyrke."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    # Luminans formel
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return 'white' if luminance < 0.5 else 'black'

def get_team_style(team_name):
    """Returnerer holdets farve (håndterer hvid-tjek) og logo."""
    color = HIF_RED
    logo_img = None
    
    if team_name in TEAM_COLORS:
        c = TEAM_COLORS[team_name]
        prim = c['primary'].lower()
        if prim in ["#ffffff", "white", "#f9f9f9"]:
            color = c.get('secondary', HIF_RED)
        else:
            color = c['primary']
            
    if team_name in TEAMS:
        url = TEAMS[team_name].get('logo')
        if url:
            logo_img = get_logo_img(url)
            
    return color, logo_img

def draw_logo(ax, logo_img):
    """Placerer logoet lidt inde mod midten i bunden."""
    if logo_img:
        # Justeret x fra 0.03 til 0.08 for at rykke det lidt mod midten
        ax_image = ax.inset_axes([0.08, 0.03, 0.12, 0.12], transform=ax.transAxes)
        ax_image.imshow(logo_img)
        ax_image.axis('off')

# --- HOVEDFUNKTION ---

def vis_side(dp):
    opta_data = dp.get('opta', {})
    df_all = opta_data.get('league_shotevents', pd.DataFrame()).copy()

    if df_all.empty:
        st.info("Ingen ligadata fundet.")
        return

    # 1. DATA FORBEREDELSE
    df_all.columns = [c.upper() for c in df_all.columns]
    col_team_uuid = 'EVENT_CONTESTANT_OPTAUUID'
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    
    df_all['KLUB_NAVN'] = df_all[col_team_uuid].str.upper().map(uuid_to_name)
    teams_in_data = sorted([name for name in df_all['KLUB_NAVN'].unique() if pd.notna(name)])

    # 2. ZONE DEFINITIONER
    P_L, P_W = 105.0, 68.0
    X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
    X_INN_L, X_INN_R = (P_W - 40.2) / 2, (P_W + 40.2) / 2
    Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0

    ZONE_BOUNDARIES = {
        "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 4A": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_R, "x_max": X_INN_R},
        "Zone 4B": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_INN_L, "x_max": X_MID_L},
        "Zone 5A": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_MID_R, "x_max": X_INN_R},
        "Zone 5B": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_INN_L, "x_max": X_MID_L},
        "Zone 6A": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": X_INN_R, "x_max": P_W},
        "Zone 6B": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": 0, "x_max": X_INN_L},
        "Zone 7C": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": 0, "x_max": X_MID_L},
        "Zone 7B": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 7A": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_R, "x_max": P_W},
        "Zone 8":  {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": P_W}
    }

    def map_to_zone(r):
        mx, my = r['EVENT_X'] * (P_L / 100), r['EVENT_Y'] * (P_W / 100)
        for z, b in ZONE_BOUNDARIES.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]: return z
        return "Zone 8"

    df_all['Zone'] = df_all.apply(map_to_zone, axis=1)
    df_all['IS_DZ_GEO'] = (df_all['EVENT_X'] >= 88.5) & (df_all['EVENT_Y'] >= 37.0) & (df_all['EVENT_Y'] <= 63.0)

    # 3. UI STYLE
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; }}
        </style>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])

    # --- TAB 0: SPILLEROVERSIGT (Fuld Oversigt Genskabt) ---
    with tabs[0]:
        stats = []
        for (p, klub), d in df_all.groupby(['PLAYER_NAME', 'KLUB_NAVN']):
            dz = d[d['IS_DZ_GEO']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            dzs, dzm = len(dz), len(dz[dz['EVENT_TYPEID'] == 16])
            stats.append({
                "Spiller": p, "Klub": klub, "Skud": s, "Mål": m, 
                "Konv.%": (m/s*100) if s > 0 else 0,
                "DZ-Skud": dzs, "DZ-Mål": dzm, 
                "DZ-Andel": (dzs/s*100) if s > 0 else 0
            })
        df_f = pd.DataFrame(stats).sort_values("Skud", ascending=False)
        st.dataframe(df_f, use_container_width=True, height=700, hide_index=True,
                    column_config={
                        "Konv.%": st.column_config.NumberColumn("Konv.%", format="%.1f%%"),
                        "DZ-Andel": st.column_config.ProgressColumn("DZ-Andel", format="%.0f%%", min_value=0, max_value=100)
                    })

    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            t_sel = st.selectbox("Vælg Hold", teams_in_data, key="t1")
            t_color, t_logo = get_team_style(t_sel)
            df_t = df_all[df_all['KLUB_NAVN'] == t_sel]
            p_sel = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_t['PLAYER_NAME'].unique()), key="p1")
            d_v = df_t if p_sel == "Hele Holdet" else df_t[df_t['PLAYER_NAME'] == p_sel]
            st.markdown(f'<div class="stat-box" style="border-left-color:{t_color}"><div class="stat-label">Skud ({t_sel})</div><div class="stat-value">{len(d_v)}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: t_color, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=35, c=colors, edgecolors=t_color, linewidth=0.8, ax=ax)
            draw_logo(ax, t_logo)
            st.pyplot(fig)

    # --- TAB 2: DZ-AFSLUTNINGER ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2:
            t_sel2 = st.selectbox("Vælg Hold", teams_in_data, key="t2")
            t_color2, t_logo2 = get_team_style(t_sel2)
            df_t2 = df_all[(df_all['KLUB_NAVN'] == t_sel2) & (df_all['IS_DZ_GEO'])]
            st.markdown(f'<div class="stat-box" style="border-left-color:{t_color2}"><div class="stat-label">Danger Zone Skud</div><div class="stat-value">{len(df_t2)}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            colors = (df_t2['EVENT_TYPEID'] == 16).map({True: t_color2, False: 'white'})
            pitch.scatter(df_t2['EVENT_X'], df_t2['EVENT_Y'], s=40, c=colors, edgecolors=t_color2, ax=ax)
            draw_logo(ax, t_logo2)
            st.pyplot(fig)

    # --- TAB 3 & 4: ZONER (Med Dynamisk Tekstfarve) ---
    def zone_tab(is_goal, k):
        c1, c2 = st.columns([1.8, 1])
        with c2:
            t_selz = st.selectbox("Vælg Hold", teams_in_data, key=f"tz{k}")
            t_colorz, t_logoz = get_team_style(t_selz)
            txt_color = get_text_color(t_colorz) # Hvid eller sort tekst
            
            df_t = df_all[df_all['KLUB_NAVN'] == t_selz]
            plot_data = df_t[df_t['EVENT_TYPEID'] == 16] if is_goal else df_t
            z_counts = plot_data.groupby('Zone').size()
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            max_v = z_counts.max() if not z_counts.empty else 1
            
            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                cnt = z_counts.get(name, 0)
                # Jo flere skud, jo højere alpha (op til 0.85)
                alpha = (cnt/max_v) * 0.85 if cnt > 0 else 0.05
                ax.add_patch(patches.Rectangle((b["x_min"], max(b["y_min"], 55)), b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55), 
                                             facecolor=t_colorz, alpha=alpha, edgecolor='black', ls='--'))
                if cnt > 0:
                    # Brug den beregnede tekstfarve for læsbarhed
                    ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, max(b["y_min"], 55)+(b["y_max"]-max(b["y_min"], 55))/2, f"{cnt}", 
                            ha='center', va='center', fontsize=10, fontweight='bold', color=txt_color)
            draw_logo(ax, t_logoz)
            st.pyplot(fig)

    with tabs[3]: zone_tab(False, "skud")
    with tabs[4]: zone_tab(True, "maal")
