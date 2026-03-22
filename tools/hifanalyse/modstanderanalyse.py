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

# --- 2. TEGNEFUNKTIONER ---
def draw_average_pitch(df_avg, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', line_zorder=2)
    fig, ax = pitch.draw(figsize=(4, 5)) 
    if not df_avg.empty:
        for _, row in df_avg.iterrows():
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

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    if not analysis_package:
        st.error("Ingen data fundet.")
        return

    df_remote = analysis_package.get("remote_shapes", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_matches = analysis_package.get("matches", pd.DataFrame())

    if df_remote.empty:
        st.warning("Ingen positionsdata tilgængelig.")
        return

    # --- AGGRESSIV MATCHING LOGIK ---
    uuids_i_data = df_remote['CONTESTANT_OPTAUUID'].unique().tolist()
    team_map = {} 

    # Hent holdnavne fra kampen som backup
    h_name = df_matches['CONTESTANTHOME_NAME'].iloc[0] if not df_matches.empty else None
    a_name = df_matches['CONTESTANTAWAY_NAME'].iloc[0] if not df_matches.empty else None

    for i, u_data in enumerate(uuids_i_data):
        u_data_clean = str(u_data).strip().lower()
        matched = False
        
        # 1. Prøv mapping via opta_uuid
        for t_name, t_info in TEAMS.items():
            t_uuid = str(t_info.get('opta_uuid', '')).strip().lower()
            if t_uuid and (t_uuid[:8] in u_data_clean or u_data_clean[:8] in t_uuid):
                team_map[t_name] = u_data
                matched = True
                break
        
        # 2. Backup: Hvis ikke mappet, brug navne fra matches-tabellen
        if not matched:
            if i == 0 and h_name:
                team_map[h_name] = u_data
            elif i == 1 and a_name:
                team_map[a_name] = u_data
            else:
                team_map[f"Hold {i+1} ({u_data_clean[:5]})"] = u_data

    # UI
    valgt_hold = st.selectbox("Vælg hold:", sorted(list(team_map.keys())))
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)
    
    # Til hændelser: find den "rene" UUID fra mapping hvis muligt
    event_uuid_ref = str(TEAMS.get(valgt_hold, {}).get('opta_uuid', valgt_uuid_data)).lower()[:8]

    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]:
        df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'] == valgt_uuid_data]
        formation = df_h['SHAPE_FORMATION'].iloc[-1] if 'SHAPE_FORMATION' in df_h.columns else "N/A"
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

    # --- EVENT TABS (Kører på event_uuid_ref) ---
    with tabs[1]:
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if not df_h_ev.empty:
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
            else: st.warning(f"Ingen hændelser fundet for {valgt_hold} med ID {event_uuid_ref}")

    # (Tabs 2 og 3 følger samme logik som Tab 1...)
