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

# --- KONSTANTER FRA DIN KONFIGURATION ---
CURRENT_SEASON = "2025/2026"

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

# --- 2. MASTER MATCHER ---
def build_team_map(df_remote, df_matches):
    # Vi filtrerer kun hold, der optræder i den nuværende sæson, hvis kolonnen findes
    if 'SEASONNAME' in df_matches.columns:
        df_matches = df_matches[df_matches['SEASONNAME'] == CURRENT_SEASON]
    
    raw_uuids = df_remote['CONTESTANT_OPTAUUID'].unique().tolist()
    team_map = {}
    mapping_lookup = {str(info.get('opta_uuid', '')).lower()[:8]: name for name, info in TEAMS.items()}
    
    db_teams = pd.DataFrame()
    if not df_matches.empty:
        home = df_matches[['CONTESTANTHOME_OPTAUUID', 'CONTESTANTHOME_NAME']].rename(columns={'CONTESTANTHOME_OPTAUUID': 'id', 'CONTESTANTHOME_NAME': 'name'})
        away = df_matches[['CONTESTANTAWAY_OPTAUUID', 'CONTESTANTAWAY_NAME']].rename(columns={'CONTESTANTAWAY_OPTAUUID': 'id', 'CONTESTANTAWAY_NAME': 'name'})
        db_teams = pd.concat([home, away]).drop_duplicates()

    for u_raw in raw_uuids:
        u_clean = str(u_raw).lower().strip()
        matched_name = None
        for m_id, name in mapping_lookup.items():
            if m_id and (m_id in u_clean or u_clean.startswith(m_id)):
                matched_name = name
                break
        if not matched_name and not db_teams.empty:
            match_row = db_teams[db_teams['id'].str.lower() == u_clean]
            if not match_row.empty: matched_name = match_row['name'].iloc[0]
        if not matched_name: matched_name = f"Ukendt ({u_clean[:6]})"
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

    # --- TJEK SÆSON ---
    # Hvis OB er i listen, er det sandsynligvis fordi din data-query henter alt fra databasen.
    # Vi tvinger den her til kun at vise hold fra 2025/2026 hvis muligt.
    team_map = build_team_map(df_remote, df_matches)
    
    if not team_map:
        st.warning(f"Ingen data fundet for sæsonen {CURRENT_SEASON}.")
        return

    valgt_hold = st.selectbox("Vælg hold:", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)
    event_uuid_ref = str(valgt_uuid_data).lower()[:8]

    st.caption(f"Viser data for: **{valgt_hold}** | Sæson: {CURRENT_SEASON}")

    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # --- TAB 0: STRUKTUR ---
    with tabs[0]:
        df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'] == valgt_uuid_data]
        formation = df_h['SHAPE_FORMATION'].iloc[-1] if 'SHAPE_FORMATION' in df_h.columns else "N/A"
        
        avg_in, avg_out = get_avg(df_h, 'inPossession'), get_avg(df_h, 'outOfPossession')
        pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', linewidth=1)
        
        c1, c2 = st.columns(2)
        for col, data, title, dot_c in zip([c1, c2], [avg_in, avg_out], ["OFFENSIV", "DEFENSIV"], [t_color, "#333333"]):
            with col:
                st.write(f"<p style='text-align:center; font-size:12px; margin-bottom:-10px;'>{title} ({formation})</p>", unsafe_allow_html=True)
                fig, ax = pitch.draw(figsize=(3, 3.8))
                if not data.empty:
                    for _, row in data.iterrows():
                        ax.scatter(row['averageRolePositionY'], row['averageRolePositionX'], s=150, color=dot_c, edgecolors='black', linewidth=0.8, zorder=3)
                        ax.text(row['averageRolePositionY'], row['averageRolePositionX'], str(int(row['shirtNumber'])), color='white', ha='center', va='center', fontsize=6, fontweight='bold', zorder=4)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

    # --- TAB 1: MED BOLD ---
    with tabs[1]:
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if not df_h_ev.empty:
                pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333', linewidth=1)
                c1, c2 = st.columns(2)
                for col, title, x_lim in zip([c1, c2], ["OPBYGNING", "AFSLUTNING"], [(0,50), (50,100)]):
                    with col:
                        st.write(f"<p style='text-align:center; font-size:12px; margin-bottom:-10px;'>{title}</p>", unsafe_allow_html=True)
                        fig, ax = pitch_h.draw(figsize=(3, 3))
                        ax.set_ylim(x_lim[0], x_lim[1])
                        df_z = df_h_ev[(df_h_ev['EVENT_TYPEID']==1) & (df_h_ev['LOCATIONX'].between(x_lim[0], x_lim[1]))]
                        if not df_z.empty:
                            sns.kdeplot(x=df_z['LOCATIONY'], y=df_z['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax, bw_adjust=0.8)
                        draw_logo_on_ax(ax, t_logo)
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)

    # --- TAB 2: MOD BOLD ---
    with tabs[2]:
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if not df_h_ev.empty:
                pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', linewidth=1)
                c1, c2 = st.columns(2)
                for col, (etype, title, cmap) in zip([c1, c2], [([4, 8, 49], "EROBRINGER", "Blues"), ([5], "DUELLER", "Greens")]):
                    with col:
                        st.write(f"<p style='text-align:center; font-size:12px; margin-bottom:-10px;'>{title}</p>", unsafe_allow_html=True)
                        fig, ax = pitch.draw(figsize=(3, 3.8))
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
                        st.subheader(label)
                        stats = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(ids)]['PLAYER_NAME'].value_counts().head(5)
                        for n, v in stats.items(): st.markdown(f"**{v}** {n}")
