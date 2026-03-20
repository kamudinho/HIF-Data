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

# --- 1. HJÆLPEFUNKTIONER ---
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
        pos = [0.05, 0.05, 0.12, 0.12] if position == 'bottom_left' else [0.05, 0.83, 0.12, 0.12]
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
        st.error("Ingen datapakke (analysis_package) modtaget fra hoved-appen.")
        return

    # --- 3. DATA PREPARATION ---
    df_matches = analysis_package.get("matches", pd.DataFrame())
    opta_dict = analysis_package.get("opta", {})
    df_events = opta_dict.get("opta_events", pd.DataFrame())
    df_in = analysis_package.get("shapes_in", pd.DataFrame())
    df_out = analysis_package.get("shapes_out", pd.DataFrame())

    # Sørg for UPPERCASE kolonner i alt
    for df in [df_events, df_in, df_out, df_matches]:
        if not df.empty:
            df.columns = [c.upper() for c in df.columns]

    # --- 4. FILTRE ---
    col_h1, col_h2 = st.columns([1, 1])
    with col_h1:
        hold_navne = sorted(df_matches['CONTESTANTHOME_NAME'].unique()) if not df_matches.empty else []
        if not hold_navne and not df_events.empty:
            hold_navne = sorted(df_events['PLAYER_NAME'].unique()) # Fallback
        
        valgt_hold = st.selectbox("Vælg hold:", hold_navne if hold_navne else ["Ingen hold fundet"], key="target_team_select")
    
    t_color, t_logo = get_team_style(valgt_hold)
    
    # Hent UUID
    hold_uuid = ""
    if not df_matches.empty:
        m_row = df_matches[df_matches['CONTESTANTHOME_NAME'] == valgt_hold]
        if not m_row.empty:
            hold_uuid = str(m_row['CONTESTANTHOME_OPTAUUID'].iloc[0])

    df_hold = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'] == hold_uuid].copy() if hold_uuid else df_events.copy()

    with col_h2:
        spiller_liste = ["Alle spillere"] + sorted(df_hold['PLAYER_NAME'].dropna().unique().tolist()) if not df_hold.empty else ["Alle spillere"]
        valgt_spiller = st.selectbox("Filter spiller:", spiller_liste, key="player_select")

    if valgt_spiller != "Alle spillere":
        df_hold = df_hold[df_hold['PLAYER_NAME'] == valgt_spiller]

    # --- 5. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # GRUNDSTRUKTUR
        # --- TVUNGEN DEBUG INFO ---
        st.write(f"**DEBUG INFO:**")
        st.write(f"- Valgt hold: {valgt_hold}")
        st.write(f"- UUID fundet: `{hold_uuid}`")
        st.write(f"- Rækker i 'shapes_in': {len(df_in)}")
        st.write(f"- Rækker i 'shapes_out': {len(df_out)}")

        # Filtrering
        df_in_h = df_in[df_in['CONTESTANT_OPTAUUID'].astype(str).str.upper() == hold_uuid.upper()].copy() if not df_in.empty else pd.DataFrame()
        df_out_h = df_out[df_out['CONTESTANT_OPTAUUID'].astype(str).str.upper() == hold_uuid.upper()].copy() if not df_out.empty else pd.DataFrame()

        def draw_shape_pitch(df_shape, title, color, logo):
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch.draw(figsize=(6, 8))
            st.markdown(f'<p class="pitch-label">{title}</p>', unsafe_allow_html=True)
            
            if not df_shape.empty:
                try:
                    top_row = df_shape.sort_values('SHAPE_TIMEINSHAPE', ascending=False).iloc[0]
                    roles_raw = top_row.get('SHAPE_ROLE', [])
                    roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw

                    if roles and isinstance(roles, list):
                        for r in roles:
                            x, y = float(r.get('averageX', 50)), float(r.get('averageY', 50))
                            ax.scatter(y, x, s=400, color=color, edgecolors='black', linewidth=1.5, zorder=3)
                            ax.text(y, x, r.get('roleShortName', ''), color='white', ha='center', va='center', fontsize=8, fontweight='bold', zorder=4)
                        draw_logo_custom(ax, logo, position='top_left')
                    else:
                        ax.text(50, 50, "Ingen JSON-positioner i rækken", ha='center', va='center', transform=ax.transAxes)
                except Exception as e:
                    ax.text(50, 50, f"Fejl i tegning: {e}", ha='center', va='center', transform=ax.transAxes)
            else:
                ax.text(50, 50, "Ingen match på UUID", ha='center', va='center', transform=ax.transAxes)
            
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        c1, c2 = st.columns(2)
        with c1:
            if not df_in_h.empty:
                prim_in = df_in_h.groupby('SHAPE_FORMATION')['SHAPE_TIMEINSHAPE'].sum().idxmax()
                st.metric("Formation", prim_in)
                draw_shape_pitch(df_in_h, "OFFENSIV POSITION", "#2ecc71", t_logo)
            else:
                st.warning("Data findes i tabellen, men ikke for dette UUID.")

        with c2:
            if not df_out_h.empty:
                prim_out = df_out_h.groupby('SHAPE_FORMATION')['SHAPE_TIMEINSHAPE'].sum().idxmax()
                st.metric("Formation", prim_out)
                draw_shape_pitch(df_out_h, "DEFENSIV POSITION", "#e74c3c", t_logo)
            else:
                st.warning("Ingen defensiv data fundet for holdet.")

    # (De resterende tabs 1, 2 og 3 bibeholdes som før...)
