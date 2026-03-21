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
        try:
            # Placerer logoet øverst til venstre (x=0.02, y=0.88)
            ax_image = ax.inset_axes([0.02, 0.88, 0.12, 0.12], transform=ax.transAxes)
            ax_image.imshow(logo_img)
            ax_image.axis('off')
        except Exception as e:
            st.write(f"Fejl ved tegning af logo: {e}")

# --- 2. TEGNEFUNKTIONER ---
def draw_remote_pitch(df_row, title, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', line_zorder=2)
    fig, ax = pitch.draw(figsize=(6, 8))
    
    # Titel
    ax.text(50, 103, title, color='black', va='center', ha='center', fontsize=14, fontweight='bold')
    
    if not df_row.empty:
        formation = df_row.get('SHAPE_FORMATION', 'N/A')
        roles_raw = df_row.get('SHAPE_ROLE', [])
        
        try:
            # Håndterer både streng og liste-input
            roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw
            
            if isinstance(roles, list):
                for r in roles:
                    # Vi bruger 'averageRolePositionX' og 'averageRolePositionY'
                    x = float(r.get('averageRolePositionX', 50))
                    y = float(r.get('averageRolePositionY', 50))
                    num = r.get('shirtNumber', '')
                    
                    # Tegn spiller
                    ax.scatter(y, x, s=700, color=color, edgecolors='black', linewidth=1.5, zorder=3)
                    ax.text(y, x, str(num), color='white', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
                
                # Formation i bunden
                ax.text(50, 2, f"Formation: {formation}", color='gray', ha='center', fontsize=10, fontweight='bold')
        except Exception as e:
            st.error(f"Fejl i JSON parsing: {e}")
            
    # TEGN LOGOET SIDST SÅ DET LIGGER ØVERST
    draw_logo_custom(ax, logo)
    
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    # Styling
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem; }
            .stat-box { background-color: #f8f9fa; padding: 10px; border-radius: 8px; margin-bottom: 8px; border-left: 5px solid #df003b; }
        </style>
    """, unsafe_allow_html=True)

    if not analysis_package:
        st.error("Ingen datapakke modtaget.")
        return

    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_remote_raw = analysis_package.get("remote_shapes", pd.DataFrame())

    # Parsing af Snowflake data
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

    # Holdvalg
    all_teams = sorted(list(set(df_matches['CONTESTANTHOME_NAME']) | set(df_matches['CONTESTANTAWAY_NAME']))) if not df_matches.empty else []
    valgt_hold = st.selectbox("Vælg hold:", all_teams, key="team_selector")
    
    t_color, t_logo = get_team_style(valgt_hold)
    
    # Debug info til dig (kan fjernes senere)
    if t_logo:
        st.success(f"Logo fundet for {valgt_hold}")
    else:
        st.warning(f"Logo IKKE fundet for {valgt_hold}. Tjek TEAMS i team_mapping.py")

    # Find UUID for holdet
    hold_uuid = ""
    if not df_matches.empty:
        m_row = df_matches[(df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold)]
        if not m_row.empty:
            hold_uuid = str(m_row['CONTESTANTHOME_OPTAUUID'].iloc[0] if m_row['CONTESTANTHOME_NAME'].iloc[0] == valgt_hold else m_row['CONTESTANTAWAY_OPTAUUID'].iloc[0]).strip().lower()

    # Tabs
    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # STRUKTUR
        if not df_remote.empty and hold_uuid:
            df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'].str.contains(hold_uuid[:15], na=False)]
            if not df_h.empty:
                t_options = sorted(df_h['SHAPE_TIMEELAPSEDSTART'].unique().tolist())
                t_step = st.select_slider("Vælg sekvens:", options=t_options)
                df_s = df_h[df_h['SHAPE_TIMEELAPSEDSTART'] == t_step]
                
                c1, c2 = st.columns(2)
                with c1:
                    df_in = df_s[df_s['POSSESSION_TYPE'] == 'inPossession']
                    draw_remote_pitch(df_in.iloc[0] if not df_in.empty else pd.Series(), "OFFENSIV", t_color, t_logo)
                with c2:
                    df_out = df_s[df_s['POSSESSION_TYPE'] == 'outOfPossession']
                    draw_remote_pitch(df_out.iloc[0] if not df_out.empty else pd.Series(), "DEFENSIV", "#333333", t_logo)

    with tabs[1]: # MED BOLD (Heatmaps som på dit screenshot)
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            with c1:
                st.write("OPBYGNING")
                fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
                df_p = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'] < 50)]
                if not df_p.empty:
                    sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax)
                draw_logo_custom(ax, t_logo)
                st.pyplot(fig); plt.close(fig)
            with c2:
                st.write("AFSLUTNING")
                fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
                df_g = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'] >= 50)]
                if not df_g.empty:
                    sns.kdeplot(x=df_g['LOCATIONY'], y=df_g['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax)
                draw_logo_custom(ax, t_logo)
                st.pyplot(fig); plt.close(fig)
                
    # ... Resten af tabs 2 og 3 (Mod bold / Top 5) følger samme mønster med draw_logo_custom(ax, t_logo)
