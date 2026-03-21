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
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def get_team_style(team_name):
    color = '#cc0000'
    logo_img = None
    if team_name in TEAM_COLORS:
        c = TEAM_COLORS[team_name]
        prim = str(c['primary']).lower()
        color = c.get('secondary', '#cc0000') if prim in ["#ffffff", "white", "#f9f9f9"] else c['primary']
    if team_name in TEAMS:
        url = TEAMS[team_name].get('logo')
        if url: logo_img = get_logo_img(url)
    return color, logo_img

def draw_logo_custom(ax, logo_img, position='top_left'):
    if logo_img:
        pos = [0.02, 0.02, 0.15, 0.15] if position == 'bottom_left' else [0.02, 0.83, 0.15, 0.15]
        ax_image = ax.inset_axes(pos, transform=ax.transAxes)
        ax_image.imshow(logo_img)
        ax_image.axis('off')

# --- 2. TEGNEFUNKTION TIL STRUKTUR ---
def draw_remote_pitch(df_row, title, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
    fig, ax = pitch.draw(figsize=(6, 8))
    st.markdown(f'<p class="pitch-label">{title}</p>', unsafe_allow_html=True)
    
    if not df_row.empty:
        formation = df_row.get('SHAPE_FORMATION', 'N/A')
        roles_raw = df_row.get('SHAPE_ROLE', [])
        
        try:
            roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw
        except:
            roles = []

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
        ax.text(50, 50, "Ingen taktisk data", ha='center', va='center')
        
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
    df_remote_raw = analysis_package.get("remote_shapes", pd.DataFrame())

    # --- 1. ROBUST PARSING AF DATASTRUKTUR ---
    processed_rows = []
    if not df_remote_raw.empty:
        # Hvis Snowflake sender en "pølse" i én kolonne
        for _, row in df_remote_raw.iterrows():
            line = str(row.iloc[0])
            
            # Find JSON delen
            json_match = re.search(r'(\[.*\])', line)
            roles = json_match.group(1) if json_match else "[]"
            
            # Find Formation (f.eks. 4-3-3 eller 3-4-2-1)
            form_match = re.findall(r'\d-\d-\d(?:-\d)?', line)
            formation = form_match[-1] if form_match else "N/A"
            
            # Find UUIDs (25 tegn alfanumerisk)
            uuids = re.findall(r'[a-z0-9]{25}', line)
            # Typisk er Contestant UUID den før eller efter formationen
            c_uuid = uuids[1] if len(uuids) > 1 else (uuids[0] if uuids else "unknown")
            
            # Possession type
            possession = "inPossession" if "inPossession" in line else "outOfPossession"
            
            # Tid (find det største tal der ligner et millisekund timestamp)
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

    # --- 2. SETUP AF HOLD & UUID ---
    col_h1, col_h2 = st.columns([1, 1])
    with col_h1:
        home_teams = df_matches['CONTESTANTHOME_NAME'].unique() if not df_matches.empty else []
        away_teams = df_matches['CONTESTANTAWAY_NAME'].unique() if not df_matches.empty else []
        hold_navne = sorted(list(set(home_teams) | set(away_teams)))
        valgt_hold = st.selectbox("Vælg hold:", hold_navne, key="target_team_select")
    
    t_color, t_logo = get_team_style(valgt_hold)
    
    hold_uuid = ""
    if not df_matches.empty:
        m_row_h = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]
        m_row_a = df_matches[df_matches['CONTESTANTAWAY_NAME'] == valgt_hold]
        if not m_row_h.empty:
            hold_uuid = str(m_row_h['CONTESTANTHOME_OPTAUUID'].iloc[0]).strip().lower()
        elif not m_row_a.empty:
            hold_uuid = str(m_row_a['CONTESTANTAWAY_OPTAUUID'].iloc[0]).strip().lower()

    with col_h2:
        df_hold_events = pd.DataFrame()
        if not df_events.empty and hold_uuid:
            match_key = hold_uuid[:15]
            df_hold_events = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(match_key, na=False)].copy()
        
        valgt_spiller = st.selectbox("Filter spiller:", ["Alle spillere"] + sorted(df_hold_events['PLAYER_NAME'].dropna().unique().tolist()))

    if valgt_spiller != "Alle spillere":
        df_hold_events = df_hold_events[df_hold_events['PLAYER_NAME'] == valgt_spiller]

    # --- 3. TABS ---
    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # STRUKTUR
        if not df_remote.empty and hold_uuid:
            # Vi matcher på de første 15 tegn for at være sikre på tværs af formater
            df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'].str.contains(hold_uuid[:15], na=False)].copy()
            
            if not df_h.empty:
                time_options = sorted(df_h['SHAPE_TIMEELAPSEDSTART'].unique().tolist())
                time_step = st.select_slider("Vælg sekvens (timestamp):", options=time_options)
                df_step = df_h[df_h['SHAPE_TIMEELAPSEDSTART'] == time_step]

                c1, c2 = st.columns(2)
                with c1:
                    df_in = df_step[df_step['POSSESSION_TYPE'].str.contains('in', na=False, case=False)]
                    draw_remote_pitch(df_in.iloc[0] if not df_in.empty else pd.DataFrame(), "OFFENSIV", "#2ecc71", t_logo)
                with c2:
                    df_out = df_step[df_step['POSSESSION_TYPE'].str.contains('out', na=False, case=False)]
                    draw_remote_pitch(df_out.iloc[0] if not df_out.empty else pd.DataFrame(), "DEFENSIV", "#e74c3c", t_logo)
            else:
                st.warning(f"Ingen taktisk data fundet for {valgt_hold}.")
        else:
            st.info("Indlæser taktisk data...")

    with tabs[1]: # MED BOLD (Heatmaps)
        if not df_hold_events.empty:
            pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            with c1:
                st.write("OPBYGNING")
                fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
                df_p = df_hold_events[(df_hold_events['EVENT_TYPEID'] == 1) & (df_hold_events['LOCATIONX'] < 50)]
                if not df_p.empty:
                    sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax, clip=((0, 100), (0, 50)), thresh=0.05)
                st.pyplot(fig); plt.close(fig)
            with c2:
                st.write("AFSLUTNINGSSPIL")
                fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
                df_g = df_hold_events[(df_hold_events['EVENT_TYPEID'] == 1) & (df_hold_events['LOCATIONX'] >= 50)]
                if not df_g.empty:
                    sns.kdeplot(x=df_g['LOCATIONY'], y=df_g['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax, clip=((0, 100), (50, 100)), thresh=0.05)
                st.pyplot(fig); plt.close(fig)

    with tabs[2]: # MOD BOLD
        if not df_hold_events.empty:
            c1, c2 = st.columns(2)
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            with c1:
                st.write("EROBRINGER")
                fig, ax = pitch.draw(figsize=(5, 7))
                df_ero = df_hold_events[df_hold_events['EVENT_TYPEID'].isin([4, 8, 49])]
                if not df_ero.empty:
                    sns.kdeplot(x=df_ero['LOCATIONY'], y=df_ero['LOCATIONX'], fill=True, cmap='Blues', alpha=0.5, ax=ax, thresh=0.05)
                st.pyplot(fig); plt.close(fig)
            with c2:
                st.write("DUELLER")
                fig, ax = pitch.draw(figsize=(5, 7))
                df_duel = df_hold_events[df_hold_events['EVENT_TYPEID'] == 5]
                if not df_duel.empty:
                    sns.kdeplot(x=df_duel['LOCATIONY'], y=df_duel['LOCATIONX'], fill=True, cmap='Greens', alpha=0.5, ax=ax, thresh=0.05)
                st.pyplot(fig); plt.close(fig)

    with tabs[3]: # TOP 5
        if not df_hold_events.empty:
            cols = st.columns(3)
            stats_config = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
            for i, (tid, nav) in enumerate(stats_config):
                with cols[i]:
                    st.markdown(f"**Top {nav}**")
                    top = df_hold_events[df_hold_events['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                    for n, count in top.items(): 
                        st.markdown(f'<div class="stat-box"><b>{count}</b> {n}</div>', unsafe_allow_html=True)
