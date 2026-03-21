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

# --- 2. DEN RETTEDE PITCH FUNKTION ---
def draw_shape_pitch(df_shape, title, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
    fig, ax = pitch.draw(figsize=(6, 8))
    st.markdown(f'<p class="pitch-label">{title}</p>', unsafe_allow_html=True)
    
    if not df_shape.empty:
        try:
            # Sorter efter mest brugte formation og tag den øverste række
            top_row = df_shape.sort_values('SHAPE_TIMEINSHAPE', ascending=False).iloc[0]
            roles_raw = top_row.get('SHAPE_ROLE', [])
            
            # Håndter JSON parsing
            roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw

            if isinstance(roles, list) and len(roles) > 0:
                for r in roles:
                    # Remote Shapes koordinater (håndterer både centreret og non-centered)
                    x = float(r.get('averageRolePositionXNonCentered') or (float(r.get('averageRolePositionX', 0)) + 50))
                    y = float(r.get('averageRolePositionYNonCentered') or (float(r.get('averageRolePositionY', 0)) + 50))
                    
                    # Tegn spiller-dot
                    ax.scatter(y, x, s=550, color=color, edgecolors='white', linewidth=1.5, zorder=3)
                    
                    # Label (f.eks. CB, CM)
                    label = r.get('roleDescription', '')
                    ax.text(y, x, label, color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
                
                draw_logo_custom(ax, logo, position='top_left')
            else:
                ax.text(50, 50, "Ingen spiller-positioner i data", ha='center', va='center', transform=ax.transAxes)
        except Exception as e:
            ax.text(50, 50, f"Fejl i data-format", ha='center', va='center', transform=ax.transAxes)
    else:
        ax.text(50, 50, "Ingen taktiske data fundet", ha='center', va='center', transform=ax.transAxes)
    
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# --- 3. HOVEDFUNKTIONEN ---
def vis_side(analysis_package=None):
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

    # Hent data fra pakken
    df_matches = analysis_package.get("matches", pd.DataFrame())
    opta_dict = analysis_package.get("opta", {})
    df_events = opta_dict.get("opta_events", pd.DataFrame())
    df_in = analysis_package.get("shapes_in", pd.DataFrame())
    df_out = analysis_package.get("shapes_out", pd.DataFrame())

    # Standardiser kolonnenavne til UPPERCASE
    for df in [df_events, df_in, df_out, df_matches]:
        if not df.empty: df.columns = [c.upper() for c in df.columns]

    if df_events.empty:
        st.warning("Venter på event-data...")
        return

    # --- 4. FILTRE & UUID OPSLAG ---
    col_h1, col_h2 = st.columns([1, 1])
    
    with col_h1:
        # Find alle mulige holdnavne fra matches, events og shapes
        all_teams = set()
        if not df_matches.empty:
            all_teams.update(df_matches['CONTESTANTHOME_NAME'].dropna().tolist())
            all_teams.update(df_matches['CONTESTANTAWAY_NAME'].dropna().tolist())
        if not df_events.empty:
            # En nødløsning hvis matches er tomme
            pass 
        
        hold_navne = sorted(list(all_teams))
        if not hold_navne: hold_navne = ["Vælg hold"]
        valgt_hold = st.selectbox("Vælg hold:", hold_navne, key="target_team_select")

    # FIND UUID (Den kritiske del)
    hold_uuid = ""
    if not df_matches.empty:
        m_row = df_matches[(df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold)]
        if not m_row.empty:
            # Tjek om det valgte hold er hjemme eller ude i den fundne række
            if m_row['CONTESTANTHOME_NAME'].iloc[0] == valgt_hold:
                hold_uuid = str(m_row['CONTESTANTHOME_OPTAUUID'].iloc[0])
            else:
                hold_uuid = str(m_row['CONTESTANTAWAY_OPTAUUID'].iloc[0])

    # Hvis UUID stadig mangler, så kig i shapes som backup
    if not hold_uuid and not df_in.empty:
         # Her har vi ikke navnet, kun UUID. Dette er en "last resort".
         pass

    # Filtrer events
    df_hold_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].astype(str).str.lower() == hold_uuid.lower()].copy() if hold_uuid else df_events.copy()

    with col_h2:
        valgt_spiller = st.selectbox("Filter spiller:", ["Alle spillere"] + sorted(df_hold_ev['PLAYER_NAME'].dropna().unique().tolist()), key="player_select")

    if valgt_spiller != "Alle spillere":
        df_hold_ev = df_hold_ev[df_hold_ev['PLAYER_NAME'] == valgt_spiller]

    t_color, t_logo = get_team_style(valgt_hold)

    # --- 5. TABS ---
    tabs = st.tabs(["GRUNDSTRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]: # GRUNDSTRUKTUR
        # Filtrer shapes specifikt på det valgte holds UUID
        df_in_h = df_in[df_in['CONTESTANT_OPTAUUID'].astype(str).str.lower() == hold_uuid.lower()].copy() if not df_in.empty and hold_uuid else pd.DataFrame()
        df_out_h = df_out[df_out['CONTESTANT_OPTAUUID'].astype(str).str.lower() == hold_uuid.lower()].copy() if not df_out.empty and hold_uuid else pd.DataFrame()

        c1, c2 = st.columns(2)
        with c1:
            if not df_in_h.empty:
                prim_in = df_in_h.groupby('SHAPE_FORMATION')['SHAPE_TIMEINSHAPE'].sum().idxmax()
                st.metric("Primær Offensiv", prim_in)
                draw_shape_pitch(df_in_h, "POSITIONS (MED BOLD)", "#2ecc71", t_logo)
            else: 
                st.info(f"Ingen offensiv data for {valgt_hold}")
                draw_shape_pitch(pd.DataFrame(), "POSITIONS (MED BOLD)", "#2ecc71", t_logo)

        with c2:
            if not df_out_h.empty:
                prim_out = df_out_h.groupby('SHAPE_FORMATION')['SHAPE_TIMEINSHAPE'].sum().idxmax()
                st.metric("Primær Defensiv", prim_out)
                draw_shape_pitch(df_out_h, "POSITIONS (MOD BOLD)", "#e74c3c", t_logo)
            else: 
                st.info(f"Ingen defensiv data for {valgt_hold}")
                draw_shape_pitch(pd.DataFrame(), "POSITIONS (MOD BOLD)", "#e74c3c", t_logo)

    with tabs[1]: # MED BOLD
        pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333', line_zorder=4)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<p class="pitch-label">OPBYGNING (0-50m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(0, 50)
            draw_logo_custom(ax, t_logo, position='bottom_left')
            df_p = df_hold_ev[(df_hold_ev['EVENT_TYPEID'] == 1) & (df_hold_ev['LOCATIONX'] < 50)]
            if not df_p.empty:
                sns.kdeplot(x=df_p['LOCATIONY'], y=df_p['LOCATIONX'], fill=True, cmap='Reds', alpha=0.4, thresh=0.05, ax=ax, zorder=2, clip=((0, 100), (0, 50)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)
        with c2:
            st.markdown('<p class="pitch-label">GENNEMBRUD (50-100m)</p>', unsafe_allow_html=True)
            fig, ax = pitch_h.draw(figsize=(6, 8)); ax.set_ylim(50, 100)
            draw_logo_custom(ax, t_logo, position='top_left')
            df_g = df_hold_ev[(df_hold_ev['EVENT_TYPEID'] == 1) & (df_hold_ev['LOCATIONX'] >= 50)]
            if not df_g.empty:
                sns.kdeplot(x=df_g['LOCATIONY'], y=df_g['LOCATIONX'], fill=True, cmap='Reds', alpha=0.4, thresh=0.05, ax=ax, zorder=2, clip=((0, 100), (50, 100)))
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
            df_ero = df_hold_ev[df_hold_ev['EVENT_TYPEID'].isin([4, 8, 49])]
            if not df_ero.empty:
                sns.kdeplot(x=df_ero['LOCATIONY'], y=df_ero['LOCATIONX'], fill=True, cmap='Blues', alpha=0.4, thresh=0.1, ax=ax, zorder=2, clip=((0, 100), (0, 100)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)
        with c2:
            st.markdown('<p style="text-align:center; font-size:12px;">DUELLER</p>', unsafe_allow_html=True)
            pitch = VerticalPitch(**pitch_cfg)
            fig, ax = pitch.draw(figsize=(5, 7))
            draw_logo_custom(ax, t_logo, position='top_left')
            df_duel = df_hold_ev[df_hold_ev['EVENT_TYPEID'] == 5]
            if not df_duel.empty:
                sns.kdeplot(x=df_duel['LOCATIONY'], y=df_duel['LOCATIONX'], fill=True, cmap='Greens', alpha=0.4, thresh=0.1, ax=ax, zorder=2, clip=((0, 100), (0, 100)))
            st.pyplot(fig, use_container_width=True); plt.close(fig)

    with tabs[3]: # TOP 5
        cols = st.columns(3)
        stats_cfg = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
        for i, (tid, nav) in enumerate(stats_cfg):
            with cols[i]:
                st.markdown(f"**Top {nav}**")
                top = df_hold_ev[df_hold_ev['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                for n, count in top.items(): 
                    st.markdown(f'<div class="stat-box"><b>{count}</b> {n}</div>', unsafe_allow_html=True)
