import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import requests
from io import BytesIO
from PIL import Image
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- 1. LOGO & FARVE HJÆLPEFUNKTIONER (Fra din fungerende ligafil) ---
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
        # Undgå hvid farve på hvid bane
        color = c.get('secondary', '#cc0000') if prim in ["#ffffff", "white", "#f9f9f9"] else c['primary']
    if team_name in TEAMS:
        url = TEAMS[team_name].get('logo')
        if url: logo_img = get_logo_img(url)
    return color, logo_img

def draw_logo_custom(ax, logo_img, position='top_left'):
    if logo_img:
        # Juster placering baseret på axes-koordinater (0 til 1)
        if position == 'bottom_left':
            pos = [0.05, 0.05, 0.12, 0.12] # x, y, bredde, højde
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
    
    # HENT LOGO OG FARVE
    t_color, t_logo = get_team_style(valgt_hold)
    
    hold_uuid = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]['CONTESTANTHOME_OPTAUUID'].iloc[0] if not df_matches.empty else ""
    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy() if hold_uuid else df_events.copy()

    with col_h2:
        valgt_spiller = st.selectbox("Filter spiller:", ["Alle spillere"] + sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist()), key="player_select")

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    # --- 5. TABS ---
    # --- 5. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # GRUNDSTRUKTUR
        df_in = analysis_package.get("shapes_in", pd.DataFrame())
        df_out = analysis_package.get("shapes_out", pd.DataFrame())

        if not df_in.empty: df_in.columns = [c.upper() for c in df_in.columns]
        if not df_out.empty: df_out.columns = [c.upper() for c in df_out.columns]

        df_in_h = df_in[df_in['CONTESTANT_OPTAUUID'] == hold_uuid].copy() if not df_in.empty else pd.DataFrame()
        df_out_h = df_out[df_out['CONTESTANT_OPTAUUID'] == hold_uuid].copy() if not df_out.empty else pd.DataFrame()

        st.markdown(f"### Taktisk Grundstruktur: {valgt_hold}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p class="pitch-label" style="color:#2ecc71;">IN POSSESSION (MED BOLD)</p>', unsafe_allow_html=True)
            if not df_in_h.empty:
                prim_in = df_in_h.groupby('SHAPE_FORMATION')['SHAPE_TIMEINSHAPE'].sum().idxmax()
                pct_in = (df_in_h[df_in_h['SHAPE_FORMATION'] == prim_in]['SHAPE_PERCENTAGEINSHAPE'].mean()) * 100
                st.metric("Primær Shape", prim_in, f"{pct_in:.1f}%")
                
                df_disp_in = df_in_h.groupby('SHAPE_FORMATION').agg({'SHAPE_TIMEINSHAPE': 'sum', 'SHAPEOUTCOME_XG': 'mean'}).rename(columns={'SHAPE_TIMEINSHAPE': 'Minutter', 'SHAPEOUTCOME_XG': 'Gns. xG'}).sort_values('Minutter', ascending=False)
                st.dataframe(df_disp_in, use_container_width=True)

        with c2:
            st.markdown('<p class="pitch-label" style="color:#e74c3c;">OUT OF POSSESSION (MOD BOLD)</p>', unsafe_allow_html=True)
            if not df_out_h.empty:
                prim_out = df_out_h.groupby('SHAPE_FORMATION')['SHAPE_TIMEINSHAPE'].sum().idxmax()
                pct_out = (df_out_h[df_out_h['SHAPE_FORMATION'] == prim_out]['SHAPE_PERCENTAGEINSHAPE'].mean()) * 100
                st.metric("Primær Shape", prim_out, f"{pct_out:.1f}%")

                df_disp_out = df_out_h.groupby('SHAPE_FORMATION').agg({'SHAPE_TIMEINSHAPE': 'sum', 'SHAPEOUTCOME_XGCONCEDED': 'mean'}).rename(columns={'SHAPE_TIMEINSHAPE': 'Minutter', 'SHAPEOUTCOME_XGCONCEDED': 'Gns. xG Imod'}).sort_values('Minutter', ascending=False)
                st.dataframe(df_disp_out, use_container_width=True)

    with tabs[1]: # MED BOLD (Rettelse af indrykning her)
        pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333', line_zorder=4)
        c1, c2 = st.columns(2)
        
        with c1: # Opbygning
            st.markdown('<p class="pitch-label">OPBYGNING (0-50m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8))
            ax.set_ylim(0, 50)
            draw_logo_custom(ax, t_logo, position='bottom_left')
            
            df_p = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] < 50)]
            if not df_p.empty:
                sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], fill=True, cmap='Reds', alpha=0.4, thresh=0.1, ax=ax, zorder=2, clip=((0, 100), (0, 50)))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        with c2: # Gennembrud
            st.markdown('<p class="pitch-label">GENNEMBRUD (50-100m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8))
            ax.set_ylim(50, 100)
            draw_logo_custom(ax, t_logo, position='top_left')
            
            df_g = df_hold[(df_hold['EVENT_TYPEID'] == 1) & (df_hold['LOCATIONX'] >= 50)]
            if not df_g.empty:
                sns.kdeplot(x=df_g['LOCATIONY'], y=df_g['LOCATIONX'], fill=True, cmap='Reds', alpha=0.4, thresh=0.1, ax=ax, zorder=2, clip=((0, 100), (50, 100)))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    with tabs[2]: # MOD BOLD
        st.markdown('<p class="pitch-label">DEFENSIV STRUKTUR</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        pitch_cfg = {"pitch_type": 'opta', "pitch_color": '#ffffff', "line_color": '#333333', "line_zorder": 4}

        with c1: # Erobringer
            st.markdown('<p style="text-align:center; font-size:12px;">EROBRINGER</p>', unsafe_allow_html=True)
            pitch = VerticalPitch(**pitch_cfg)
            fig, ax = pitch.draw(figsize=(5, 7))
            draw_logo_custom(ax, t_logo, position='top_left')
            
            df_ero = df_hold[df_hold['EVENT_TYPEID'].isin([4, 8, 49])]
            if not df_ero.empty:
                sns.kdeplot(x=df_ero['LOCATIONY'], y=df_ero['LOCATIONX'], fill=True, cmap='Blues', alpha=0.4, thresh=0.1, ax=ax, zorder=2, clip=((0, 100), (0, 100)))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        with c2: # Dueller
            st.markdown('<p style="text-align:center; font-size:12px;">DUELLER</p>', unsafe_allow_html=True)
            pitch = VerticalPitch(**pitch_cfg)
            fig, ax = pitch.draw(figsize=(5, 7))
            draw_logo_custom(ax, t_logo, position='top_left')
            
            df_duel = df_hold[df_hold['EVENT_TYPEID'] == 5]
            if not df_duel.empty:
                sns.kdeplot(x=df_duel['LOCATIONY'], y=df_duel['LOCATIONX'], fill=True, cmap='Greens', alpha=0.4, thresh=0.1, ax=ax, zorder=2, clip=((0, 100), (0, 100)))
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    with tabs[3]: # TOP 5
        cols = st.columns(3)
        for i, (tid, nav) in enumerate([([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]):
            with cols[i]:
                st.markdown(f"**Top {nav}**")
                top = df_hold[df_hold['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                for n, count in top.items(): 
                    st.markdown(f'<div class="stat-box"><b>{count}</b> {n}</div>', unsafe_allow_html=True)
