import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import VerticalPitch
import requests
from io import BytesIO
from PIL import Image
import json
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- 1. HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(url):
    if not url: return None
    try:
        response = requests.get(url, timeout=3)
        return Image.open(BytesIO(response.content))
    except: return None

def get_team_style(team_name):
    default_color = '#df003b'
    color = default_color
    logo_img = None
    if not team_name: return color, None

    clean_name = str(team_name).lower().replace(' if', '').replace(' fc', '').strip()
    
    # Farve-match
    team_color_match = next((v for k, v in TEAM_COLORS.items() if clean_name in k.lower()), None)
    if team_color_match:
        prim = str(team_color_match.get('primary', default_color)).lower()
        color = team_color_match.get('secondary', default_color) if prim in ["#ffffff", "white", "#f9f9f9"] else prim

    # Logo-match
    team_info_match = next((v for k, v in TEAMS.items() if clean_name in k.lower()), None)
    if team_info_match:
        logo_img = get_logo_img(team_info_match.get('logo'))
        
    return color, logo_img

def draw_logo_custom(ax, logo_img, position='top_left'):
    if logo_img:
        pos = [0.02, 0.85, 0.12, 0.12] if position == 'top_left' else [0.02, 0.02, 0.12, 0.12]
        ax_image = ax.inset_axes(pos, transform=ax.transAxes)
        ax_image.imshow(logo_img)
        ax_image.axis('off')

# NY FUNKTION: Skaber en farveskala fra gennemsigtig til holdets farve
def get_team_cmap(color):
    return LinearSegmentedColormap.from_list("team_cmap", ["#ffffff00", color])

# --- 2. PITCH FUNKTIONER ---
def draw_shape_pitch(df_shape, title, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
    fig, ax = pitch.draw(figsize=(6, 8))
    if not df_shape.empty:
        try:
            top_row = df_shape.sort_values('SHAPE_TIMEINSHAPE', ascending=False).iloc[0]
            roles = json.loads(top_row['SHAPE_ROLE']) if isinstance(top_row['SHAPE_ROLE'], str) else top_row['SHAPE_ROLE']
            for r in roles:
                x = float(r.get('averageRolePositionXNonCentered') or (float(r.get('averageRolePositionX', 0)) + 50))
                y = float(r.get('averageRolePositionYNonCentered') or (float(r.get('averageRolePositionY', 0)) + 50))
                ax.scatter(y, x, s=550, color=color, edgecolors='white', linewidth=1.5, zorder=3)
                ax.text(y, x, r.get('roleDescription', ''), color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
            draw_logo_custom(ax, logo)
        except: ax.text(50, 50, "Fejl i data", ha='center')
    st.markdown(f'<p class="pitch-label">{title}</p>', unsafe_allow_html=True)
    st.pyplot(fig); plt.close(fig)

# --- 3. HOVEDFUNKTIONEN ---
def vis_side(analysis_package=None):
    if not analysis_package: return

    # Data Setup
    df_matches = analysis_package.get("matches", pd.DataFrame()).copy()
    opta_dict = analysis_package.get("opta", {})
    df_events = opta_dict.get("opta_events", pd.DataFrame()).copy()
    df_in = analysis_package.get("shapes_in", pd.DataFrame()).copy()
    df_out = analysis_package.get("shapes_out", pd.DataFrame()).copy()

    for df in [df_matches, df_events, df_in, df_out]:
        if not df.empty: df.columns = [c.upper() for c in df.columns]

    # Vælg hold & hent stil
    h_name = df_matches['CONTESTANTHOME_NAME'].iloc[0]
    a_name = df_matches['CONTESTANTAWAY_NAME'].iloc[0]
    valgt_hold = st.selectbox("Vælg hold:", sorted([h_name, a_name]))
    
    t_color, t_logo = get_team_style(valgt_hold)
    t_cmap = get_team_cmap(t_color) # Skaber holdets heatmap-farve

    # Find UUID
    row = df_matches.iloc[0]
    hold_uuid = str(row['CONTESTANTHOME_OPTAUUID']).lower() if row['CONTESTANTHOME_NAME'] == valgt_hold else str(row['CONTESTANTAWAY_OPTAUUID']).lower()

    # Filtrer events
    df_hold_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].astype(str).str.lower() == hold_uuid].copy() if not df_events.empty else pd.DataFrame()

    tabs = st.tabs(["STRUKTUR", "OFFENSIV", "DEFENSIV"])

    with tabs[0]: # Struktur
        c1, c2 = st.columns(2)
        with c1: draw_shape_pitch(df_in[df_in['CONTESTANT_OPTAUUID'].astype(str).str.lower() == hold_uuid], "MED BOLD", t_color, t_logo)
        with c2: draw_shape_pitch(df_out[df_out['CONTESTANT_OPTAUUID'].astype(str).str.lower() == hold_uuid], "MOD BOLD", "#333333", t_logo)

    with tabs[1]: # Offensiv (Nu med holdfarve og logo)
        if not df_hold_ev.empty:
            pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            for i, (col, title, x_range) in enumerate(zip([c1, c2], ["OPBYGNING", "AFSLUTNING"], [(0, 50), (50, 100)])):
                with col:
                    st.markdown(f'<p class="pitch-label">{title}</p>', unsafe_allow_html=True)
                    fig, ax = pitch.draw(figsize=(6, 8)); ax.set_ylim(x_range)
                    df_p = df_hold_ev[(df_hold_ev['EVENT_TYPEID'] == 1) & (df_hold_ev['LOCATIONX'].between(*x_range))]
                    if not df_p.empty:
                        sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], fill=True, cmap=t_cmap, alpha=0.7, ax=ax, clip=((0,100), x_range))
                    draw_logo_custom(ax, t_logo) # Tilføjet logo til heatmap
                    st.pyplot(fig); plt.close(fig)

    with tabs[2]: # Defensiv (Nu med holdfarve og logo)
        if not df_hold_ev.empty:
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            types = [([4, 8, 49], "EROBRINGER"), ([5], "DUELLER")]
            for col, (t_ids, title) in zip([c1, c2], types):
                with col:
                    st.markdown(f'<p class="pitch-label">{title}</p>', unsafe_allow_html=True)
                    fig, ax = pitch.draw(figsize=(6, 8))
                    df_d = df_hold_ev[df_hold_ev['EVENT_TYPEID'].isin(t_ids)]
                    if not df_d.empty:
                        sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], fill=True, cmap=t_cmap, alpha=0.7, ax=ax)
                    draw_logo_custom(ax, t_logo) # Tilføjet logo til heatmap
                    st.pyplot(fig); plt.close(fig)
