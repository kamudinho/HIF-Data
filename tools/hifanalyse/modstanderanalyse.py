import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import requests
from io import BytesIO
from PIL import Image
import json
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- 1. LOGO & FARVE HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def get_team_style(team_name):
    color = '#cc0000'
    logo_img = None
    if team_name in TEAM_COLORS:
        c = TEAM_COLORS[team_name]
        prim = c['primary'].lower()
        color = c.get('secondary', '#cc0000') if prim in ["#ffffff", "white", "#f9f9f9"] else c['primary']
    if team_name in TEAMS:
        url = TEAMS[team_name].get('logo')
        if url: logo_img = get_logo_img(url)
    return color, logo_img

def draw_logo_custom(ax, logo_img, position='top_left'):
    if logo_img:
        # Justeret placering og størrelse for bedre synlighed
        pos = [0.02, 0.02, 0.15, 0.15] if position == 'bottom_left' else [0.02, 0.83, 0.15, 0.15]
        ax_image = ax.inset_axes(pos, transform=ax.transAxes)
        ax_image.imshow(logo_img)
        ax_image.axis('off')

# --- 2. TEGNEFUNKTION TIL STRUKTUR (MED LOGO & RYGNUMRE) ---
def draw_remote_pitch(df_row, title, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
    fig, ax = pitch.draw(figsize=(6, 8))
    st.markdown(f'<p class="pitch-label">{title}</p>', unsafe_allow_html=True)
    
    if not df_row.empty:
        formation = df_row.get('SHAPE_FORMATION', 'N/A')
        roles_raw = df_row.get('SHAPE_ROLE', [])
        roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw

        if isinstance(roles, list):
            for r in roles:
                x = float(r.get('averageRolePositionX', 50))
                y = float(r.get('averageRolePositionY', 50))
                num = r.get('shirtNumber', '')
                
                ax.scatter(y, x, s=550, color=color, edgecolors='black', linewidth=1.5, zorder=3)
                ax.text(y, x, str(num), color='white', ha='center', va='center', fontsize=10, fontweight='bold', zorder=4)
            
            ax.text(50, 4, f"Formation: {formation}", color='black', ha='center', fontsize=12, fontweight='bold')
            draw_logo_custom(ax, logo, position='top_left')
    else:
        ax.text(50, 50, "Ingen data fundet", ha='center', va='center')
        
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem; }
            .stat-box { 
                background-color: #f8f9fa; padding: 8px; border-radius: 6px; 
                border-left: 4px solid #df003b; margin-bottom: 5px; font-size: 0.85rem;
            }
            .pitch-label { text-align: center; font-weight: bold; font-size: 16px; margin-bottom: 5px; }
        </style>
    """, unsafe_allow_html=True)

    if not analysis_package:
        st.error("Ingen datapakke modtaget.")
        return

    df_matches = analysis_package.get("matches", pd.DataFrame())
    opta_dict = analysis_package.get("opta", {})
    df_events = opta_dict.get("events", pd.DataFrame())
    df_remote = analysis_package.get("remote_shapes", pd.DataFrame())

    # --- 4. FILTRE ---
    col_h1, col_h2 = st.columns([1, 1])
    with col_h1:
        hold_navne = sorted(df_matches['CONTESTANTHOME_NAME'].unique()) if not df_matches.empty else []
        valgt_hold = st.selectbox("Vælg hold:", hold_navne, key="target_team_select")
    
    t_color, t_logo = get_team_style(valgt_hold)
    
    hold_uuid = ""
    if not df_matches.empty:
        m_row = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]
        if not m_row.empty: 
            hold_uuid = str(m_row['CONTESTANTHOME_OPTAUUID'].iloc[0])

    with col_h2:
        df_hold_events = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy() if not df_events.empty else pd.DataFrame()
        valgt_spiller = st.selectbox("Filter spiller:", ["Alle spillere"] + sorted(df_hold_events['PLAYER_NAME'].dropna().unique().tolist()))

    if valgt_spiller != "Alle spillere":
        df_hold_events = df_hold_events[df_hold_events['PLAYER_NAME'] == valgt_spiller]

    # --- 5. TABS ---
    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # STRUKTUR
        if not df_remote.empty and hold_uuid:
            df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'] == hold_uuid].copy()
            st.write("### Kampforløb & Taktik")
            time_step = st.select_slider("Vælg tidsinterval (minutter):", options=sorted(df_h['SHAPE_TIMEELAPSEDSTART'].unique().tolist()))
            df_step = df_h[df_h['SHAPE_TIMEELAPSEDSTART'] == time_step]

            c1, c2 = st.columns(2)
            with c1:
                df_in = df_step[df_step['POSSESSION_TYPE'] == 'inPossession']
                row_in = df_in.iloc[0] if not df_in.empty else pd.DataFrame()
                draw_remote_pitch(row_in, "OFFENSIV STRUKTUR", "#2ecc71", t_logo)
            with c2:
                df_out = df_step[df_step['POSSESSION_TYPE'] == 'outOfPossession']
                row_out = df_out.iloc[0] if not df_out.empty else pd.DataFrame()
                draw_remote_pitch(row_out, "DEFENSIV STRUKTUR", "#e74c3c", t_logo)
        else:
            st.info("Ingen taktisk data fundet.")

    with tabs[1]: # MED BOLD (OPDATERET MED CLIP)
        pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING (0-50m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
            draw_logo_custom(ax, t_logo, position='bottom_left')
            df_p = df_hold_events[(df_hold_events['EVENT_TYPEID'] == 1) & (df_hold_events['LOCATIONX'] < 50)]
            if not df_p.empty:
                sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], fill=True, cmap='Reds', 
                            alpha=0.5, ax=ax, clip=((0, 100), (0, 50)), thresh=0.05, levels=50)
            st.pyplot(fig); plt.close(fig)
        with c2:
            st.markdown('<p class="pitch-label">GENNEMBRUD (50-100m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
            draw_logo_custom(ax, t_logo, position='top_left')
            df_g = df_hold_events[(df_hold_events['EVENT_TYPEID'] == 1) & (df_hold_events['LOCATIONX'] >= 50)]
            if not df_g.empty:
                sns.kdeplot(x=df_g['LOCATIONY'], y=df_g['LOCATIONX'], fill=True, cmap='Reds', 
                            alpha=0.5, ax=ax, clip=((0, 100), (50, 100)), thresh=0.05, levels=50)
            st.pyplot(fig); plt.close(fig)

    with tabs[2]: # MOD BOLD (OPDATERET MED CLIP)
        c1, c2 = st.columns(2)
        with c1:
            st.write("EROBRINGER")
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch.draw(figsize=(5, 7))
            draw_logo_custom(ax, t_logo, position='top_left')
            df_ero = df_hold_events[df_hold_events['EVENT_TYPEID'].isin([4, 8, 49])]
            if not df_ero.empty:
                sns.kdeplot(x=df_ero['LOCATIONY'], y=df_ero['LOCATIONX'], fill=True, cmap='Blues', 
                            alpha=0.5, ax=ax, clip=((0, 100), (0, 100)), thresh=0.05)
            st.pyplot(fig); plt.close(fig)
        with c2:
            st.write("DUELLER")
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch.draw(figsize=(5, 7))
            draw_logo_custom(ax, t_logo, position='top_left')
            df_duel = df_hold_events[df_hold_events['EVENT_TYPEID'] == 5]
            if not df_duel.empty:
                sns.kdeplot(x=df_duel['LOCATIONY'], y=df_duel['LOCATIONX'], fill=True, cmap='Greens', 
                            alpha=0.5, ax=ax, clip=((0, 100), (0, 100)), thresh=0.05)
            st.pyplot(fig); plt.close(fig)

    with tabs[3]: # TOP 5
        cols = st.columns(3)
        stats_config = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
        for i, (tid, nav) in enumerate(stats_config):
            with cols[i]:
                st.markdown(f"**Top {nav}**")
                top = df_hold_events[df_hold_events['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                for n, count in top.items(): 
                    st.markdown(f'<div class="stat-box"><b>{count}</b> {n}</div>', unsafe_allow_html=True)
