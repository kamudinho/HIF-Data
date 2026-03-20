import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import requests
from io import BytesIO
from PIL import Image
import json  # Vigtigt til parsing af positions-data
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- 1. LOGO & FARVE HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def get_team_style(team_name):
    color = '#cc0000' # Default rød
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
        if position == 'bottom_left':
            pos = [0.05, 0.05, 0.12, 0.12]
        else: # top_left
            pos = [0.05, 0.83, 0.12, 0.12]
        ax_image = ax.inset_axes(pos, transform=ax.transAxes)
        ax_image.imshow(logo_img)
        ax_image.axis('off')

def vis_side(analysis_package=None):
    # --- 2. UI & CSS ---
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem; }
            .stat-box { 
                background-color: #f8f9fa; padding: 8px; border-radius: 6px; 
                border-left: 4px solid #df003b; margin-bottom: 5px; font-size: 0.85rem;
            }
            .pitch-label { text-align: center; font-weight: bold; font-size: 14px; margin-bottom: 5px; }
            div[data-testid="stSelectbox"] label { display: none; }
        </style>
    """, unsafe_allow_html=True)

    if not analysis_package:
        st.error("Ingen datapakke modtaget.")
        return

    # --- 3. DATA HÅNDTERING ---
    df_matches = analysis_package.get("matches", pd.DataFrame())
    opta_dict = analysis_package.get("opta", {})
    df_events = opta_dict.get("opta_events", pd.DataFrame())

    if df_events.empty:
        st.warning("Ingen event-data fundet.")
        return

    df_events.columns = [c.upper() for c in df_events.columns]

    # --- 4. FILTRE ---
    col_h1, col_h2 = st.columns([1, 1])
    with col_h1:
        hold_navne = sorted(df_matches['CONTESTANTHOME_NAME'].unique()) if not df_matches.empty else sorted(df_events['PLAYER_NAME'].unique())
        valgt_hold = st.selectbox("Vælg hold:", hold_navne, key="target_team_select")
    
    t_color, t_logo = get_team_style(valgt_hold)
    
    # Hent hold UUID
    hold_uuid = ""
    if not df_matches.empty:
        match_row = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]
        if not match_row.empty:
            hold_uuid = match_row['CONTESTANTHOME_OPTAUUID'].iloc[0]

    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy() if hold_uuid else df_events.copy()

    with col_h2:
        valgt_spiller = st.selectbox("Filter spiller:", ["Alle spillere"] + sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist()), key="player_select")

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    # --- 5. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # GRUNDSTRUKTUR
        df_in = analysis_package.get("shapes_in", pd.DataFrame())
        df_out = analysis_package.get("shapes_out", pd.DataFrame())

        if not df_in.empty: df_in.columns = [c.upper() for c in df_in.columns]
        if not df_out.empty: df_out.columns = [c.upper() for c in df_out.columns]

        df_in_h = df_in[df_in['CONTESTANT_OPTAUUID'] == hold_uuid].copy() if not df_in.empty else pd.DataFrame()
        df_out_h = df_out[df_out['CONTESTANT_OPTAUUID'] == hold_uuid].copy() if not df_out.empty else pd.DataFrame()
        
        # Intern hjælpefunktion til at tegne banen
        def draw_shape_pitch(df_shape, title, color, logo):
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch.draw(figsize=(6, 8))
            st.markdown(f'<p class="pitch-label">{title}</p>', unsafe_allow_html=True)
            
            if not df_shape.empty:
                top_row = df_shape.sort_values('SHAPE_TIMEINSHAPE', ascending=False).iloc[0]
                roles_raw = top_row.get('SHAPE_ROLE', [])
                
                # Konverter JSON-streng til liste hvis nødvendigt
                roles = []
                try:
                    if isinstance(roles_raw, str):
                        roles = json.loads(roles_raw)
                    else:
                        roles = roles_raw
                except: roles = []

                if isinstance(roles, list) and len(roles) > 0:
                    for role in roles:
                        x = float(role.get('averageX', 50))
                        y = float(role.get('averageY', 50))
                        ax.scatter(y, x, s=400, color=color, edgecolors='black', linewidth=1.5, zorder=3, alpha=0.9)
                        ax.text(y, x, role.get('roleShortName', ''), color='white', ha='center', va='center', fontsize=8, fontweight='bold', zorder=4)
                    draw_logo_custom(ax, logo, position='top_left')
                else:
                    ax.text(50, 50, "Ingen positionsdata", ha='center', va='center', transform=ax.transAxes)
            else:
                ax.text(50, 50, "Ingen data", ha='center', va='center', transform=ax.transAxes)
            
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        c1, c2 = st.columns(2)

        with c1:
            if not df_in_h.empty:
                prim_in = df_in_h.groupby('SHAPE_FORMATION')['SHAPE_TIMEINSHAPE'].sum().idxmax()
                st.metric("Primær Offensiv", prim_in)
                draw_shape_pitch(df_in_h, "POSITIONS (MED BOLD)", "#2ecc71", t_logo)
                st.dataframe(df_in_h[['SHAPE_FORMATION', 'SHAPE_TIMEINSHAPE', 'SHAPEOUTCOME_XG']].head(3), hide_index=True)
            else: st.info("Ingen offensiv data")

        with c2:
            if not df_out_h.empty:
                prim_out = df_out_h.groupby('SHAPE_FORMATION')['SHAPE_TIMEINSHAPE'].sum().idxmax()
                st.metric("Primær Defensiv", prim_out)
                draw_shape_pitch(df_out_h, "POSITIONS (MOD BOLD)", "#e74c3c", t_logo)
                st.dataframe(df_out_h[['SHAPE_FORMATION', 'SHAPE_TIMEINSHAPE', 'SHAPEOUTCOME_XGCONCEDED']].head(3), hide_index=True)
            else: st.info("Ingen defensiv data")

    with tabs[1]: # MED BOLD
        pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333', line_zorder=4)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING (0-50m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
            draw_logo_custom(ax, t_logo, position='bottom_left')
            df_p = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] < 50)]
            if not df_p.empty:
                sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], fill=True, cmap='Reds', alpha=0.4, thresh=0.1, ax=ax, zorder=2, clip=((0, 100), (0, 50)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)
        with c2:
            st.markdown('<p class="pitch-label">GENNEMBRUD (50-100m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
            draw_logo_custom(ax, t_logo, position='top_left')
            df_g = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] >= 50)]
            if not df_g.empty:
                sns.kdeplot(x=df_g['LOCATIONY'], y=df_g['LOCATIONX'], fill=True, cmap='Reds', alpha=0.4, thresh=0.1, ax=ax, zorder=2, clip=((0, 100), (50, 100)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)

    with tabs[2]: # MOD BOLD
        st.markdown('<p class="pitch-label">DEFENSIV STRUKTUR</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        pitch_cfg = {"pitch_type": 'opta', "pitch_color": '#ffffff', "line_color": '#333333', "line_zorder": 4}
        with c1:
            st.markdown('<p style="text-align:center; font-size:12px;">EROBRINGER</p>', unsafe_allow_html=True)
            pitch = VerticalPitch(**pitch_cfg)
            fig, ax = pitch.draw(figsize=(5, 7))
            draw_logo_custom(ax, t_logo, position='top_left')
            df_ero = df_hold[df_hold['EVENT_TYPEID'].isin([4, 8, 49])]
            if not df_ero.empty:
                sns.kdeplot(x=df_ero['LOCATIONY'], y=df_ero['LOCATIONX'], fill=True, cmap='Blues', alpha=0.4, thresh=0.1, ax=ax, zorder=2, clip=((0, 100), (0, 100)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)
        with c2:
            st.markdown('<p style="text-align:center; font-size:12px;">DUELLER</p>', unsafe_allow_html=True)
            pitch = VerticalPitch(**pitch_cfg)
            fig, ax = pitch.draw(figsize=(5, 7))
            draw_logo_custom(ax, t_logo, position='top_left')
            df_duel = df_hold[df_hold['EVENT_TYPEID'] == 5]
            if not df_duel.empty:
                sns.kdeplot(x=df_duel['LOCATIONY'], y=df_duel['LOCATIONX'], fill=True, cmap='Greens', alpha=0.4, thresh=0.1, ax=ax, zorder=2, clip=((0, 100), (0, 100)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)

    with tabs[3]: # TOP 5
        cols = st.columns(3)
        for i, (tid, nav) in enumerate([([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]):
            with cols[i]:
                st.markdown(f"**Top {nav}**")
                top = df_hold[df_hold['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                for n, count in top.items(): 
                    st.markdown(f'<div class="stat-box"><b>{count}</b> {n}</div>', unsafe_allow_html=True)
