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
    if not url: return None
    try:
        response = requests.get(url, timeout=3)
        return Image.open(BytesIO(response.content))
    except: return None

def get_team_style(team_name):
    color = '#cc0000' # Default rød
    logo_img = None
    if team_name in TEAM_COLORS:
        c = TEAM_COLORS[team_name]
        prim = str(c.get('primary', '#cc0000')).lower()
        # Hvis primær er hvid, brug sekundær farve til prikkerne
        color = c.get('secondary', '#cc0000') if prim in ["#ffffff", "white", "#f9f9f9"] else c.get('primary', '#cc0000')
    if team_name in TEAMS:
        url = TEAMS[team_name].get('logo')
        logo_img = get_logo_img(url)
    return color, logo_img

def draw_logo_custom(ax, logo_img, position='top_left'):
    if logo_img:
        pos = [0.05, 0.05, 0.12, 0.12] if position == 'bottom_left' else [0.05, 0.83, 0.12, 0.12]
        ax_image = ax.inset_axes(pos, transform=ax.transAxes)
        ax_image.imshow(logo_img)
        ax_image.axis('off')

# --- 2. PITCH FUNKTION (Taktisk struktur) ---
def draw_shape_pitch(df_shape, title, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
    fig, ax = pitch.draw(figsize=(6, 8))
    st.markdown(f'<p class="pitch-label">{title}</p>', unsafe_allow_html=True)
    
    if not df_shape.empty:
        try:
            top_row = df_shape.sort_values('SHAPE_TIMEINSHAPE', ascending=False).iloc[0]
            roles_raw = top_row.get('SHAPE_ROLE', [])
            roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw

            if isinstance(roles, list) and len(roles) > 0:
                for r in roles:
                    # Håndterer både centrerede og rå koordinater
                    x = float(r.get('averageRolePositionXNonCentered') or (float(r.get('averageRolePositionX', 0)) + 50))
                    y = float(r.get('averageRolePositionYNonCentered') or (float(r.get('averageRolePositionY', 0)) + 50))
                    
                    ax.scatter(y, x, s=550, color=color, edgecolors='white', linewidth=1.5, zorder=3)
                    label = r.get('roleDescription', '')
                    ax.text(y, x, label, color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
                draw_logo_custom(ax, logo, position='top_left')
        except:
            ax.text(50, 50, "Kunne ikke tegne formation", ha='center', va='center', transform=ax.transAxes)
    else:
        ax.text(50, 50, "Ingen taktisk data fundet", ha='center', va='center', transform=ax.transAxes)
    
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# --- 3. HOVEDFUNKTIONEN ---
def vis_side(analysis_package=None):
    # CSS Styling
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

    # --- DATA INDLÆSNING & KOLONNE FIX ---
    df_matches = analysis_package.get("matches", pd.DataFrame()).copy()
    opta_dict = analysis_package.get("opta", {})
    df_events = opta_dict.get("opta_events", pd.DataFrame()).copy()
    df_in = analysis_package.get("shapes_in", pd.DataFrame()).copy()
    df_out = analysis_package.get("shapes_out", pd.DataFrame()).copy()

    # Tving alle kolonnenavne til UPPERCASE for at undgå 'KeyError'
    for df in [df_matches, df_events, df_in, df_out]:
        if not df.empty:
            df.columns = [c.upper() for c in df.columns]

    if df_events.empty:
        st.warning("Ingen event-data fundet for denne kamp.")
        return

    # --- FILTRE (Hold & Spiller) ---
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        # Find alle hold i kampen
        teams_in_match = []
        if 'CONTESTANTHOME_NAME' in df_matches.columns:
            teams_in_match = sorted([df_matches['CONTESTANTHOME_NAME'].iloc[0], df_matches['CONTESTANTAWAY_NAME'].iloc[0]])
        else:
            # Fallback hvis matches-tabellen driller
            teams_in_match = sorted(df_events['TEAM_NAME'].unique().tolist()) if 'TEAM_NAME' in df_events.columns else ["Vælg hold"]
            
        valgt_hold = st.selectbox("Vælg hold:", teams_in_match, key="team_sel")

    # Find UUID for det valgte hold (vigtigt for filtrering)
    hold_uuid = ""
    if not df_matches.empty:
        row = df_matches.iloc[0]
        if row['CONTESTANTHOME_NAME'] == valgt_hold:
            hold_uuid = str(row['CONTESTANTHOME_OPTAUUID']).lower()
        else:
            hold_uuid = str(row['CONTESTANTAWAY_OPTAUUID']).lower()

    # Filtrer events på holdet
    df_hold_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].astype(str).str.lower() == hold_uuid].copy() if hold_uuid else df_events.copy()

    with col_f2:
        spiller_liste = ["Alle spillere"] + sorted(df_hold_ev['PLAYER_NAME'].dropna().unique().tolist())
        valgt_spiller = st.selectbox("Vælg spiller:", spiller_liste, key="player_sel")

    if valgt_spiller != "Alle spillere":
        df_hold_ev = df_hold_ev[df_hold_ev['PLAYER_NAME'] == valgt_spiller]

    t_color, t_logo = get_team_style(valgt_hold)

    # --- TABS ---
    tabs = st.tabs(["STRUKTUR", "OFFENSIV", "DEFENSIV", "TOP 5"])

    with tabs[0]: # GRUNDSTRUKTUR (SHAPES)
        df_in_h = df_in[df_in['CONTESTANT_OPTAUUID'].astype(str).str.lower() == hold_uuid] if not df_in.empty and hold_uuid else pd.DataFrame()
        df_out_h = df_out[df_out['CONTESTANT_OPTAUUID'].astype(str).str.lower() == hold_uuid] if not df_out.empty and hold_uuid else pd.DataFrame()
        
        c1, c2 = st.columns(2)
        with c1:
            draw_shape_pitch(df_in_h, "MED BOLD", t_color, t_logo)
        with c2:
            draw_shape_pitch(df_out_h, "MOD BOLD", "#333333", t_logo)

    with tabs[1]: # OFFENSIV (HEATMAPS)
        pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING (0-50m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
            df_p = df_hold_ev[(df_hold_ev['EVENT_TYPEID'] == 1) & (df_hold_ev['LOCATIONX'] < 50)]
            if not df_p.empty:
                sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax, clip=((0,100),(0,50)))
            st.pyplot(fig); plt.close(fig)
        with c2:
            st.markdown('<p class="pitch-label">AFSLUTNING (50-100m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
            df_g = df_hold_ev[(df_hold_ev['EVENT_TYPEID'] == 1) & (df_hold_ev['LOCATIONX'] >= 50)]
            if not df_g.empty:
                sns.kdeplot(x=df_g['LOCATIONY'], y=df_g['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax, clip=((0,100),(50,100)))
            st.pyplot(fig); plt.close(fig)

    with tabs[2]: # DEFENSIV
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p class="pitch-label">EROBRINGER</p>', unsafe_allow_html=True)
            p = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            fig, ax = p.draw(figsize=(5, 7))
            df_ero = df_hold_ev[df_hold_ev['EVENT_TYPEID'].isin([4, 8, 49])]
            if not df_ero.empty:
                sns.kdeplot(x=df_ero['LOCATIONY'], y=df_ero['LOCATIONX'], fill=True, cmap='Blues', alpha=0.5, ax=ax)
            st.pyplot(fig); plt.close(fig)
        with c2:
            st.markdown('<p class="pitch-label">DUELLER</p>', unsafe_allow_html=True)
            p = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            fig, ax = p.draw(figsize=(5, 7))
            df_duel = df_hold_ev[df_hold_ev['EVENT_TYPEID'] == 5]
            if not df_duel.empty:
                sns.kdeplot(x=df_duel['LOCATIONY'], y=df_duel['LOCATIONX'], fill=True, cmap='Greens', alpha=0.5, ax=ax)
            st.pyplot(fig); plt.close(fig)

    with tabs[3]: # TOP 5 LISTER
        cols = st.columns(3)
        metrics = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
        for i, (tid, nav) in enumerate(metrics):
            with cols[i]:
                st.markdown(f"**Top {nav}**")
                top = df_hold_ev[df_hold_ev['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                for name, val in top.items():
                    st.markdown(f'<div class="stat-box"><b>{val}</b> {name}</div>', unsafe_allow_html=True)
