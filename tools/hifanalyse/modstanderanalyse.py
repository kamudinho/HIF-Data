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

def draw_logo_on_ax(ax, logo_img):
    """Universal funktion til at placere logoet korrekt på enhver akse"""
    if logo_img:
        try:
            ax_image = ax.inset_axes([0.02, 0.88, 0.12, 0.12], transform=ax.transAxes)
            ax_image.imshow(logo_img)
            ax_image.axis('off')
        except:
            pass

# --- 2. TEGNEFUNKTION TIL STRUKTUR (TAB 0) ---
def draw_remote_pitch(df_row, title, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', line_zorder=2)
    fig, ax = pitch.draw(figsize=(6, 8))
    
    ax.text(50, 103, title, color='black', va='center', ha='center', fontsize=14, fontweight='bold')
    
    if not df_row.empty:
        formation = df_row.get('SHAPE_FORMATION', 'N/A')
        roles_raw = df_row.get('SHAPE_ROLE', [])
        
        try:
            roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw
            if isinstance(roles, list):
                for r in roles:
                    x = float(r.get('averageRolePositionX', 50))
                    y = float(r.get('averageRolePositionY', 50))
                    num = r.get('shirtNumber', '')
                    
                    ax.scatter(y, x, s=700, color=color, edgecolors='black', linewidth=1.5, zorder=3)
                    ax.text(y, x, str(num), color='white', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
                
                ax.text(50, 2, f"Formation: {formation}", color='gray', ha='center', fontsize=10, fontweight='bold')
        except:
            pass
            
    draw_logo_on_ax(ax, logo)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# --- 3. HOVEDFUNKTION ---
# --- 3. HOVEDFUNKTION (OPDATERET TIL AT HÅNDTERE DINE 3 LINJER) ---
def vis_side(analysis_package=None):
    st.markdown("<style>.block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)

    if not analysis_package:
        st.error("Ingen data fundet.")
        return

    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_remote_raw = analysis_package.get("remote_shapes", pd.DataFrame())

    # --- 1. PARSING AF REMOTE SHAPES ---
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
            times = re.findall(r'\d{10,13}', line)
            t_start = int(times[0]) if times else 0
            
            processed_rows.append({
                'CONTESTANT_OPTAUUID': c_uuid.strip().lower(),
                'SHAPE_FORMATION': formation,
                'SHAPE_ROLE': roles,
                'POSSESSION_TYPE': "inPossession" if "inPossession" in line else "outOfPossession",
                'SHAPE_TIMEELAPSEDSTART': t_start
            })
    df_remote = pd.DataFrame(processed_rows)

    # --- 2. HOLDVALG & UUID ---
    all_teams = sorted(list(set(df_matches['CONTESTANTHOME_NAME']) | set(df_matches['CONTESTANTAWAY_NAME']))) if not df_matches.empty else []
    valgt_hold = st.selectbox("Vælg hold:", all_teams)
    t_color, t_logo = get_team_style(valgt_hold)

    hold_uuid = ""
    if not df_matches.empty:
        m_row = df_matches[(df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold)]
        if not m_row.empty:
            hold_uuid = str(m_row['CONTESTANTHOME_OPTAUUID'].iloc[0] if m_row['CONTESTANTHOME_NAME'].iloc[0] == valgt_hold else m_row['CONTESTANTAWAY_OPTAUUID'].iloc[0]).strip().lower()

    # --- 3. TABS ---
    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # STRUKTUR
        if not df_remote.empty and hold_uuid:
            # Filtrer på holdet
            df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'].str.contains(hold_uuid[:15], na=False)]
            
            if not df_h.empty:
                # Vi laver to sliders eller én fælles - her bruger vi én fælles tidsslider
                t_options = sorted(df_h['SHAPE_TIMEELAPSEDSTART'].unique().tolist())
                t_step = st.select_slider("Vælg sekvens:", options=t_options)
                
                # Hent data for det valgte tidspunkt
                df_current = df_h[df_h['SHAPE_TIMEELAPSEDSTART'] == t_step]
                
                c1, c2 = st.columns(2)
                with c1:
                    # Finder den nyeste 'inPossession' for dette tidspunkt (eller før)
                    df_in = df_h[(df_h['POSSESSION_TYPE'] == 'inPossession') & (df_h['SHAPE_TIMEELAPSEDSTART'] <= t_step)].last('1s') # Simpelt fallback
                    # Men for at være præcis med dine 3 linjer:
                    df_in_exact = df_current[df_current['POSSESSION_TYPE'] == 'inPossession']
                    draw_remote_pitch(df_in_exact.iloc[0] if not df_in_exact.empty else pd.Series(), "OFFENSIV (MED BOLD)", t_color, t_logo)
                
                with c2:
                    # Finder den nyeste 'outOfPossession'
                    df_out_exact = df_current[df_current['POSSESSION_TYPE'] == 'outOfPossession']
                    draw_remote_pitch(df_out_exact.iloc[0] if not df_out_exact.empty else pd.Series(), "DEFENSIV (MOD BOLD)", "#333333", t_logo)
            else:
                st.warning("Ingen taktiske data fundet for dette hold.")
                
    with tabs[1]: # MED BOLD (Heatmaps)
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            for i, (col, title, x_range) in enumerate(zip([c1, c2], ["OPBYGNING", "AFSLUTNING"], [(0, 50), (50, 100)])):
                with col:
                    st.write(f"**{title}**")
                    fig, ax = pitch_h.draw(figsize=(6, 8))
                    ax.set_ylim(x_range[0], x_range[1])
                    df_z = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'] >= x_range[0]) & (df_h_ev['LOCATIONX'] < x_range[1])]
                    if not df_z.empty:
                        sns.kdeplot(x=df_z['LOCATIONY'], y=df_z['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax)
                    draw_logo_on_ax(ax, t_logo)
                    st.pyplot(fig); plt.close(fig)

    with tabs[2]: # MOD BOLD
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            for col, (etype, title, cmap) in zip([c1, c2], [([4, 8, 49], "EROBRINGER", "Blues"), ([5], "DUELLER", "Greens")]):
                with col:
                    st.write(f"**{title}**")
                    fig, ax = pitch.draw(figsize=(5, 7))
                    df_d = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(etype)]
                    if not df_d.empty:
                        sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], fill=True, cmap=cmap, alpha=0.5, ax=ax)
                    draw_logo_on_ax(ax, t_logo)
                    st.pyplot(fig); plt.close(fig)

    with tabs[3]: # TOP 5
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            cols = st.columns(3)
            for i, (tid, nav) in enumerate([([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]):
                with cols[i]:
                    st.subheader(nav)
                    top = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                    for name, val in top.items():
                        st.markdown(f'<div class="stat-box"><b>{val}</b> {name}</div>', unsafe_allow_html=True)
