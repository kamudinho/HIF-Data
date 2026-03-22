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
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def get_team_style(team_name):
    color = '#df003b' 
    logo_img = None
    if team_name in TEAM_COLORS:
        c = TEAM_COLORS[team_name]
        prim = str(c.get('primary', '#df003b')).lower()
        color = c.get('secondary', '#333333') if prim in ["#ffffff", "white", "#f9f9f9"] else prim
    if team_name in TEAMS:
        url = TEAMS[team_name].get('logo')
        if url: logo_img = get_logo_img(url)
    return color, logo_img

def draw_logo_on_ax(ax, logo_img):
    if logo_img:
        try:
            ax_image = ax.inset_axes([0.02, 0.88, 0.12, 0.12], transform=ax.transAxes)
            ax_image.imshow(logo_img)
            ax_image.axis('off')
        except: pass

# --- 2. LOGIK TIL AT FINDE HOLD I DATA ---
def find_teams_in_data(df_remote):
    uuids_i_data = df_remote['CONTESTANT_OPTAUUID'].unique().tolist()
    found_mapping = {} # Navn -> Original UUID fra data
    
    for u_in_data in uuids_i_data:
        u_clean = str(u_in_data).strip().lower()
        
        for team_name, info in TEAMS.items():
            target_uuid = str(info.get('optauuid', '')).strip().lower()
            # Fuzzy match: Tjek om det ene ID findes i det andet (min. 8 tegn)
            if target_uuid and len(target_uuid) > 5:
                if target_uuid[:10] in u_clean or u_clean[:10] in target_uuid:
                    found_mapping[team_name] = u_in_data
                    break
    return found_mapping

# --- 3. TEGNEFUNKTIONER ---
def draw_average_pitch(df_avg, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', line_zorder=2)
    fig, ax = pitch.draw(figsize=(4, 5)) 
    if not df_avg.empty:
        for _, row in df_avg.iterrows():
            # Opta positions er 0-100. VerticalPitch håndterer dette.
            x, y = row['averageRolePositionX'], row['averageRolePositionY']
            num = row['shirtNumber']
            ax.scatter(y, x, s=250, color=color, edgecolors='black', linewidth=1, alpha=0.9, zorder=3)
            ax.text(y, x, str(int(num)), color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
    draw_logo_on_ax(ax, logo)
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)

def get_average_shape(df_hold, possession_type):
    df_fase = df_hold[df_hold['POSSESSION_TYPE'].str.contains(possession_type, case=False, na=False)]
    all_players = []
    for _, row in df_fase.iterrows():
        roles = row.get('SHAPE_ROLE', [])
        if isinstance(roles, str):
            try: roles = json.loads(roles)
            except: roles = []
        if isinstance(roles, list):
            for r in roles: all_players.append(r)
    
    if not all_players: return pd.DataFrame()
    df_p = pd.DataFrame(all_players)
    df_p['averageRolePositionX'] = pd.to_numeric(df_p['averageRolePositionX'], errors='coerce')
    df_p['averageRolePositionY'] = pd.to_numeric(df_p['averageRolePositionY'], errors='coerce')
    return df_p.groupby('shirtNumber').agg({'averageRolePositionX': 'mean', 'averageRolePositionY': 'mean'}).reset_index()

# --- 4. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    st.markdown("<style>.block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)
    
    if not analysis_package:
        st.error("Ingen pakke fundet.")
        return

    df_remote = analysis_package.get("remote_shapes", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())

    if df_remote.empty:
        st.warning("Ingen positionsdata tilgængelig.")
        return

    # Find hold baseret på din TEAMS mapping
    team_map = find_teams_in_data(df_remote)
    
    if not team_map:
        st.error("Kunne ikke matche holdene i dataen med din team_mapping.py")
        st.write("UUIDs fundet i data:", df_remote['CONTESTANT_OPTAUUID'].unique().tolist())
        return

    # Holdvælger
    valgt_hold = st.selectbox("Vælg hold:", sorted(list(team_map.keys())))
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)

    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # --- TAB 0: STRUKTUR ---
    with tabs[0]:
        df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'] == valgt_uuid_data]
        # Hent formation fra seneste række
        formation = df_h['SHAPE_FORMATION'].iloc[-1] if 'SHAPE_FORMATION' in df_h.columns else ""
        st.subheader(f"{valgt_hold} - Formation: {formation}")
        
        avg_in = get_average_shape(df_h, 'inPossession')
        avg_out = get_average_shape(df_h, 'outOfPossession')
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption("🔴 **OFFENSIV STRUKTUR**")
            draw_average_pitch(avg_in, t_color, t_logo)
        with c2:
            st.caption("⚪ **DEFENSIV STRUKTUR**")
            draw_average_pitch(avg_out, "#333333", t_logo)

    # --- TABS FOR EVENTS (Heatmaps & Top 5) ---
    # Fix: Brug de første 8 tegn af det mappede hold-ID fra din TEAMS fil til hændelser
    mapped_optauuid = str(TEAMS[valgt_hold].get('optauuid', '')).lower()[:8]

    with tabs[1]: # MED BOLD
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(mapped_optauuid, na=False)]
            if df_h_ev.empty:
                st.info("Ingen hændelser fundet for dette hold.")
            else:
                pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
                c1, c2 = st.columns(2)
                for col, title, x_range in zip([c1, c2], ["OPBYGNING", "AFSLUTNING"], [(0, 50), (50, 100)]):
                    with col:
                        st.write(f"**{title}**")
                        fig, ax = pitch_h.draw(figsize=(4, 5))
                        ax.set_ylim(x_range[0], x_range[1])
                        df_z = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'] >= x_range[0]) & (df_h_ev['LOCATIONX'] < x_range[1])]
                        if not df_z.empty:
                            sns.kdeplot(x=df_z['LOCATIONY'], y=df_z['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax, bw_adjust=0.8)
                        draw_logo_on_ax(ax, t_logo); st.pyplot(fig); plt.close(fig)

    with tabs[2]: # MOD BOLD
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(mapped_optauuid, na=False)]
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            for col, (etype, title, cmap) in zip([c1, c2], [([4, 8, 49], "EROBRINGER", "Blues"), ([5], "DUELLER", "Greens")]):
                with col:
                    st.write(f"**{title}**")
                    fig, ax = pitch.draw(figsize=(4, 5))
                    df_d = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(etype)]
                    if not df_d.empty:
                        sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], fill=True, cmap=cmap, alpha=0.5, ax=ax, bw_adjust=0.8)
                    draw_logo_on_ax(ax, t_logo); st.pyplot(fig); plt.close(fig)

    with tabs[3]: # TOP 5
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(mapped_optauuid, na=False)]
            cols = st.columns(3)
            metrics = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
            for i, (tid, nav) in enumerate(metrics):
                with cols[i]:
                    st.subheader(nav)
                    top = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                    for name, val in top.items():
                        st.markdown(f"**{val}** {name}")
