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

def get_avg(df, phase):
    df_f = df[df['POSSESSION_TYPE'].str.contains(phase, case=False, na=False)]
    all_p = []
    for r in df_f['SHAPE_ROLE']:
        try:
            roles = json.loads(r) if isinstance(r, str) else r
            if isinstance(roles, list): all_p.extend(roles)
        except: continue
    if not all_p: return pd.DataFrame()
    res = pd.DataFrame(all_p)
    res[['averageRolePositionX', 'averageRolePositionY']] = res[['averageRolePositionX', 'averageRolePositionY']].apply(pd.to_numeric)
    return res.groupby('shirtNumber').agg({'averageRolePositionX':'mean', 'averageRolePositionY':'mean'}).reset_index()

# --- 2. MASTER MATCHER (Logikken der manglede) ---
def build_team_map(df_remote, df_matches):
    # Filtrér til 1. division (NordicBet Liga = 328)
    if 'COMPETITION_WYID' in df_matches.columns:
        df_matches = df_matches[df_matches['COMPETITION_WYID'] == 328]
    
    ids_i_ligaen = pd.concat([
        df_matches['CONTESTANTHOME_OPTAUUID'], 
        df_matches['CONTESTANTAWAY_OPTAUUID']
    ]).unique()
    
    team_map = {}
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    
    for u_raw in ids_i_ligaen:
        if pd.isna(u_raw): continue
        u_clean = str(u_raw).lower().strip().replace('t', '')
        matched_name = None
        
        # Tjek TEAMS mapping
        for m_id, name in mapping_lookup.items():
            if m_id and (m_id in u_clean or u_clean in m_id):
                matched_name = name
                break
        
        # Hvis ikke i TEAMS, tjek df_matches for navn
        if not matched_name:
            match_row = df_matches[df_matches['CONTESTANTHOME_OPTAUUID'] == u_raw]
            if not match_row.empty:
                matched_name = match_row['CONTESTANTHOME_NAME'].iloc[0]
            else:
                match_away = df_matches[df_matches['CONTESTANTAWAY_OPTAUUID'] == u_raw]
                if not match_away.empty:
                    matched_name = match_away['CONTESTANTAWAY_NAME'].iloc[0]

        if not matched_name:
            matched_name = f"Ukendt ({u_clean[:5]})"
            
        team_map[matched_name] = u_raw
    return team_map

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    if not analysis_package:
        st.error("Ingen data fundet.")
        return

    df_remote = analysis_package.get("remote_shapes", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_matches = analysis_package.get("matches", pd.DataFrame())

    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # 1. Byg mappet og vælg hold
    team_map = build_team_map(df_remote, df_matches)
    valgte_hold_liste = sorted(list(team_map.keys()))
    
    if not valgte_hold_liste:
        st.warning("Ingen hold fundet for den valgte turnering.")
        return

    valgt_hold = st.selectbox("Vælg hold:", valgte_hold_liste, label_visibility="collapsed")
    
    # 2. Definer variabler
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)
    event_uuid_ref = str(valgt_uuid_data).lower().replace('t', '')[:8]

    # 3. Definer tabs og pitch
    tabs = st.tabs(["MED BOLD", "MOD BOLD", "TOP 5"])
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', linewidth=1)


    # --- TAB 1: MED BOLD ---
    with tabs[1]:
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)].copy()
            if not df_h_ev.empty:
                fokus = st.radio("Fokus:", ["Opbygning", "Gennembrud"], horizontal=True)
                c1, c2 = st.columns(2)
                if fokus == "Opbygning":
                    # Målspark
                    with c1:
                        st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>MÅLSPARK</p>", unsafe_allow_html=True)
                        df_kick = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'] < 15)]
                        fig, ax = pitch.draw(figsize=(4, 5))
                        ax.set_ylim(0, 35) 
                        if not df_kick.empty:
                            sns.kdeplot(x=df_kick['LOCATIONY'], y=df_kick['LOCATIONX'], fill=True, cmap='Reds', alpha=0.6, ax=ax, bw_adjust=0.8)
                        draw_logo_on_ax(ax, t_logo)
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)
                    # Opbygning
                    with c2:
                        st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>OPBYGNING</p>", unsafe_allow_html=True)
                        df_build = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'].between(15, 50))]
                        fig, ax = pitch.draw(figsize=(4, 5))
                        ax.set_ylim(0, 60)
                        if not df_build.empty:
                            sns.kdeplot(x=df_build['LOCATIONY'], y=df_build['LOCATIONX'], fill=True, cmap='Reds', alpha=0.6, ax=ax, bw_adjust=0.8)
                        draw_logo_on_ax(ax, t_logo)
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)
                else:
                    # Gennembrud
                    with c1:
                        st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>GENNEMBRUD</p>", unsafe_allow_html=True)
                        df_final = df_h_ev[df_h_ev['LOCATIONX'] > 66]
                        fig, ax = pitch.draw(figsize=(4, 5))
                        ax.set_ylim(60, 100)
                        if not df_final.empty:
                            sns.kdeplot(x=df_final['LOCATIONY'], y=df_final['LOCATIONX'], fill=True, cmap='Oranges', alpha=0.6, ax=ax, bw_adjust=0.8)
                        draw_logo_on_ax(ax, t_logo)
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)
                    # Progressive
                    with c2:
                        st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>PROGRESSIVE</p>", unsafe_allow_html=True)
                        df_h_ev['dist'] = ((df_h_ev['ENDLOCATIONX'] - df_h_ev['LOCATIONX'])**2 + (df_h_ev['ENDLOCATIONY'] - df_h_ev['LOCATIONY'])**2)**0.5
                        df_prog = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['dist'] > 20) & (df_h_ev['ENDLOCATIONX'] > df_h_ev['LOCATIONX'])]
                        fig, ax = pitch.draw(figsize=(4, 5))
                        ax.set_ylim(40, 100)
                        if not df_prog.empty:
                            pitch.arrows(df_prog.LOCATIONX, df_prog.LOCATIONY, df_prog.ENDLOCATIONX, df_prog.ENDLOCATIONY, width=1.5, color=t_color, ax=ax, alpha=0.5)
                        draw_logo_on_ax(ax, t_logo)
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)

    # --- TAB 2: MOD BOLD ---
    with tabs[2]:
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if not df_h_ev.empty:
                c1, c2 = st.columns(2)
                for col, (etype, title, cmap) in zip([c1, c2], [([4, 8, 49], "EROBRINGER", "Blues"), ([5], "DUELLER", "Greens")]):
                    with col:
                        st.write(f"<p style='text-align:center; font-size:11px; margin-bottom:-15px;'>{title}</p>", unsafe_allow_html=True)
                        fig, ax = pitch.draw(figsize=(3, 4))
                        df_d = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(etype)]
                        if not df_d.empty:
                            sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], fill=True, cmap=cmap, alpha=0.5, ax=ax, bw_adjust=0.8)
                        draw_logo_on_ax(ax, t_logo)
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)

    # --- TAB 3: TOP 5 ---
    with tabs[3]:
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if not df_h_ev.empty:
                c1, c2, c3 = st.columns(3)
                metrics = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
                for col, (ids, label) in zip([c1, c2, c3], metrics):
                    with col:
                        st.write(f"**{label}**")
                        stats = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(ids)]['PLAYER_NAME'].value_counts().head(5)
                        for n, v in stats.items(): st.write(f"{v} {n}")
