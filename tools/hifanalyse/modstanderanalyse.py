import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import requests
from io import BytesIO
from PIL import Image
import json
import re
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- 1. LOGO & FARVE HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(url):
    if not url:
        return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except:
        return None

def get_team_style(team_name):
    color = '#df003b' 
    logo_img = None
    if team_name in TEAM_COLORS:
        c = TEAM_COLORS[team_name]
        prim = str(c.get('primary', '#df003b')).lower()
        color = c.get('secondary', '#333333') if prim in ["#ffffff", "white", "#f9f9f9"] else prim
    
    if team_name in TEAMS:
        url = TEAMS[team_name].get('logo')
        if url:
            logo_img = get_logo_img(url)
    return color, logo_img

def draw_logo_custom(ax, logo_img):
    if logo_img:
        # Fast placering: [x_start, y_start, bredde, højde] i relativ akse-størrelse (0-1)
        # Vi placerer det i øverste venstre hjørne
        ax_image = ax.inset_axes([0.02, 0.88, 0.10, 0.10], transform=ax.transAxes)
        ax_image.imshow(logo_img)
        ax_image.axis('off')

# --- 2. TEGNEFUNKTIONER ---
def draw_remote_pitch(df_row, title, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
    fig, ax = pitch.draw(figsize=(6, 8))
    ax.text(50, 102, title, color='black', va='center', ha='center', fontsize=14, fontweight='bold')
    
    if not df_row.empty:
        formation = df_row.get('SHAPE_FORMATION', 'N/A')
        roles_raw = df_row.get('SHAPE_ROLE', [])
        try:
            roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw
            if isinstance(roles, list):
                for r in roles:
                    x, y = float(r.get('averageRolePositionX', 50)), float(r.get('averageRolePositionY', 50))
                    num = r.get('shirtNumber', '')
                    ax.scatter(y, x, s=600, color=color, edgecolors='black', linewidth=1.5, zorder=3)
                    ax.text(y, x, str(num), color='white', ha='center', va='center', fontsize=10, fontweight='bold', zorder=4)
                ax.text(50, 4, f"Formation: {formation}", color='gray', ha='center', fontsize=10)
        except: pass
        draw_logo_custom(ax, logo)
    
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    st.markdown("<style>.block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)

    if not analysis_package:
        st.error("Ingen data.")
        return

    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_remote_raw = analysis_package.get("remote_shapes", pd.DataFrame())

    # 1. Parsing
    processed_rows = []
    if not df_remote_raw.empty:
        for _, row in df_remote_raw.iterrows():
            line = str(row.iloc[0])
            json_match = re.search(r'(\[.*\])', line)
            roles = json_match.group(1) if json_match else "[]"
            form_match = re.findall(r'\d-\d-\d(?:-\d)?', line)
            formation = form_match[-1] if form_match else "N/A"
            uuids = re.findall(r'[a-z0-9]{25}', line)
            c_uuid = uuids[1] if len(uuids) > 1 else (uuids[0] if uuids else "unknown")
            processed_rows.append({'CONTESTANT_OPTAUUID': c_uuid.strip().lower(), 'SHAPE_FORMATION': formation, 'SHAPE_ROLE': roles, 'POSSESSION_TYPE': "inPossession" if "inPossession" in line else "outOfPossession", 'SHAPE_TIMEELAPSEDSTART': int(re.findall(r'\d{10,13}', line)[0]) if re.findall(r'\d{10,13}', line) else 0})
    df_remote = pd.DataFrame(processed_rows)

    # 2. Holdvalg
    all_teams = sorted(list(set(df_matches['CONTESTANTHOME_NAME']) | set(df_matches['CONTESTANTAWAY_NAME']))) if not df_matches.empty else []
    valgt_hold = st.selectbox("Vælg hold:", all_teams)
    
    # Hent stil og logo
    t_color, t_logo = get_team_style(valgt_hold)
    
    # DEBUG: Fjern denne når det virker
    if t_logo is None:
        st.warning(f"Kunne ikke finde logo for {valgt_hold}. Tjek team_mapping.py")

    # Find UUID
    hold_uuid = ""
    if not df_matches.empty:
        m_row = df_matches[(df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold)]
        if not m_row.empty:
            hold_uuid = str(m_row['CONTESTANTHOME_OPTAUUID'].iloc[0] if m_row['CONTESTANTHOME_NAME'].iloc[0] == valgt_hold else m_row['CONTESTANTAWAY_OPTAUUID'].iloc[0]).strip().lower()

    # 3. Tabs
    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # STRUKTUR
        if not df_remote.empty and hold_uuid:
            df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'].str.contains(hold_uuid[:15], na=False)]
            if not df_h.empty:
                t_options = sorted(df_h['SHAPE_TIMEELAPSEDSTART'].unique().tolist())
                t_step = st.select_slider("Tidspunkt:", options=t_options)
                df_s = df_h[df_h['SHAPE_TIMEELAPSEDSTART'] == t_step]
                c1, c2 = st.columns(2)
                with c1: draw_remote_pitch(df_s[df_s['POSSESSION_TYPE'] == 'inPossession'].iloc[0] if not df_s[df_s['POSSESSION_TYPE'] == 'inPossession'].empty else pd.Series(), "OFFENSIV", t_color, t_logo)
                with c2: draw_remote_pitch(df_s[df_s['POSSESSION_TYPE'] == 'outOfPossession'].iloc[0] if not df_s[df_s['POSSESSION_TYPE'] == 'outOfPossession'].empty else pd.Series(), "DEFENSIV", "#333333", t_logo)

    with tabs[1]: # MED BOLD (Det du ser på billedet)
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            with c1:
                fig, ax = pitch.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
                df_zone = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'] < 50)]
                if not df_zone.empty: sns.kdeplot(x=df_zone['LOCATIONY'], y=df_zone['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax)
                draw_logo_custom(ax, t_logo) # LOGO HER
                st.pyplot(fig); plt.close(fig)
            with c2:
                fig, ax = pitch.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
                df_zone = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'] >= 50)]
                if not df_zone.empty: sns.kdeplot(x=df_zone['LOCATIONY'], y=df_zone['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax)
                draw_logo_custom(ax, t_logo) # LOGO HER
                st.pyplot(fig); plt.close(fig)
