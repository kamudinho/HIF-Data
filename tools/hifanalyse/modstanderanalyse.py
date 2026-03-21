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
    color = '#df003b' # Standard HIF rød
    logo_img = None
    
    # Hent farve fra mapping
    if team_name in TEAM_COLORS:
        c = TEAM_COLORS[team_name]
        prim = str(c.get('primary', '#df003b')).lower()
        color = c.get('secondary', '#333333') if prim in ["#ffffff", "white", "#f9f9f9"] else prim
    
    # Hent logo-billede
    if team_name in TEAMS:
        url = TEAMS[team_name].get('logo')
        if url:
            logo_img = get_logo_img(url)
            
    return color, logo_img

def draw_logo_custom(ax, logo_img, position='top_left'):
    if logo_img:
        # Juster placering [x, y, bredde, højde]
        pos = [0.02, 0.85, 0.12, 0.12] if position == 'top_left' else [0.02, 0.02, 0.12, 0.12]
        ax_image = ax.inset_axes(pos, transform=ax.transAxes)
        ax_image.imshow(logo_img)
        ax_image.axis('off')

# --- 2. TEGNEFUNKTION TIL STRUKTUR (TAB 0) ---
def draw_remote_pitch(df_row, title, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', line_zorder=2)
    fig, ax = pitch.draw(figsize=(6, 8))
    
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    if not df_row.empty:
        formation = df_row.get('SHAPE_FORMATION', 'N/A')
        roles_raw = df_row.get('SHAPE_ROLE', [])
        
        try:
            roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw
        except:
            roles = []

        if isinstance(roles, list):
            for r in roles:
                # Opta koordinater (X=længde, Y=bredde). VerticalPitch vil have (Y, X)
                x = float(r.get('averageRolePositionX', 50))
                y = float(r.get('averageRolePositionY', 50))
                num = r.get('shirtNumber', '')
                
                ax.scatter(y, x, s=700, color=color, edgecolors='black', linewidth=1.5, zorder=3)
                ax.text(y, x, str(num), color='white', ha='center', va='center', fontsize=12, fontweight='bold', zorder=4)
            
            ax.text(50, 2, f"Formation: {formation}", color='black', ha='center', fontsize=12, fontweight='bold', zorder=5)
            draw_logo_custom(ax, logo, position='top_left')
    else:
        ax.text(50, 50, "Ingen data for denne sekvens", ha='center', va='center', color='gray')
        
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# --- 3. HOVEDFUNKTION (EXPORT) ---
def vis_side(analysis_package=None):
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem; }
            .stat-box { 
                background-color: #f8f9fa; padding: 10px; border-radius: 8px; 
                margin-bottom: 8px; border-left: 5px solid #df003b;
            }
            .pitch-label { text-align: center; font-weight: bold; font-size: 18px; color: #333; }
        </style>
    """, unsafe_allow_html=True)

    if not analysis_package:
        st.error("Datapakken er tom.")
        return

    # Udpak data
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_remote_raw = analysis_package.get("remote_shapes", pd.DataFrame())

    # --- 1. ROBUST PARSING AF SNOWFLAKE "PØLSE-DATA" ---
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
            possession = "inPossession" if "inPossession" in line else "outOfPossession"
            times = re.findall(r'\d{10,13}', line)
            t_start = int(times[0]) if times else 0
            
            processed_rows.append({
                'CONTESTANT_OPTAUUID': c_uuid.strip().lower(),
                'SHAPE_FORMATION': formation,
                'SHAPE_ROLE': roles,
                'POSSESSION_TYPE': possession,
                'SHAPE_TIMEELAPSEDSTART': t_start
            })
    df_remote = pd.DataFrame(processed_rows)

    # --- 2. HOLDVALG & LOGO-LOGIK ---
    all_teams = sorted(list(set(df_matches['CONTESTANTHOME_NAME']) | set(df_matches['CONTESTANTAWAY_NAME']))) if not df_matches.empty else []
    valgt_hold = st.selectbox("Vælg hold:", all_teams)
    
    t_color, t_logo = get_team_style(valgt_hold)
    
    # Find UUID (VIGTIGT: tjekker både Home og Away)
    hold_uuid = ""
    if not df_matches.empty:
        match_row = df_matches[(df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold)]
        if not match_row.empty:
            if match_row['CONTESTANTHOME_NAME'].iloc[0] == valgt_hold:
                hold_uuid = str(match_row['CONTESTANTHOME_OPTAUUID'].iloc[0]).strip().lower()
            else:
                hold_uuid = str(match_row['CONTESTANTAWAY_OPTAUUID'].iloc[0]).strip().lower()

    # --- 3. TABS ---
    tabs = st.tabs(["STRUKTUR", "OFFENSIV", "DEFENSIV", "STATISTIK"])

    with tabs[0]: # STRUKTUR
        if not df_remote.empty and hold_uuid:
            df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'].str.contains(hold_uuid[:15], na=False)].copy()
            if not df_h.empty:
                time_options = sorted(df_h['SHAPE_TIMEELAPSEDSTART'].unique().tolist())
                t_step = st.select_slider("Tidspunkt i kampen:", options=time_options)
                df_step = df_h[df_h['SHAPE_TIMEELAPSEDSTART'] == t_step]
                
                c1, c2 = st.columns(2)
                with c1:
                    df_in = df_step[df_step['POSSESSION_TYPE'] == 'inPossession']
                    draw_remote_pitch(df_in.iloc[0] if not df_in.empty else pd.Series(), "MED BOLD", t_color, t_logo)
                with c2:
                    df_out = df_step[df_step['POSSESSION_TYPE'] == 'outOfPossession']
                    draw_remote_pitch(df_out.iloc[0] if not df_out.empty else pd.Series(), "UDEN BOLD", "#333333", t_logo)
            else:
                st.warning("Ingen taktisk data fundet for dette hold.")

    with tabs[1]: # OFFENSIV (Heatmaps)
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            for i, (col, zone) in enumerate(zip([c1, c2], ["Opbygning", "Afslutning"])):
                with col:
                    st.markdown(f'<p class="pitch-label">{zone}</p>', unsafe_allow_html=True)
                    fig, ax = pitch.draw(figsize=(6, 8))
                    loc_filter = (df_h_ev['LOCATIONX'] < 50) if i == 0 else (df_h_ev['LOCATIONX'] >= 50)
                    df_zone = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & loc_filter]
                    if not df_zone.empty:
                        sns.kdeplot(x=df_zone['LOCATIONY'], y=df_zone['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax, clip=((0, 100), (0, 100 if i==1 else 50)))
                    draw_logo_custom(ax, t_logo)
                    st.pyplot(fig); plt.close(fig)

    with tabs[2]: # DEFENSIV
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            c1, c2 = st.columns(2)
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            for col, (etype, title, cmap) in zip([c1, c2], [([4, 8, 49], "Erobringer", "Blues"), ([5], "Dueller", "Greens")]):
                with col:
                    st.markdown(f'<p class="pitch-label">{title}</p>', unsafe_allow_html=True)
                    fig, ax = pitch.draw(figsize=(5, 7))
                    df_d = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(etype)]
                    if not df_d.empty:
                        sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], fill=True, cmap=cmap, alpha=0.5, ax=ax)
                    draw_logo_custom(ax, t_logo)
                    st.pyplot(fig); plt.close(fig)

    with tabs[3]: # STATISTIK
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            cols = st.columns(3)
            for i, (tid, nav) in enumerate([([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]):
                with cols[i]:
                    st.subheader(nav)
                    top = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                    for name, val in top.items():
                        st.markdown(f'<div class="stat-box"><b>{val}</b> {name}</div>', unsafe_allow_html=True)
