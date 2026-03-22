import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import requests
from io import BytesIO
from PIL import Image
import json

# Vi importerer dine mappings
try:
    from data.utils.team_mapping import TEAMS, TEAM_COLORS
except ImportError:
    TEAMS = {}
    TEAM_COLORS = {}

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

# --- 2. TEGNEFUNKTION TIL STRUKTUR ---
def draw_average_pitch(df_avg, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', line_zorder=2)
    fig, ax = pitch.draw(figsize=(4, 5)) 
    if not df_avg.empty:
        for _, row in df_avg.iterrows():
            x, y = row['averageRolePositionX'], row['averageRolePositionY']
            num = row['shirtNumber']
            ax.scatter(y, x, s=250, color=color, edgecolors='black', linewidth=1, alpha=0.9, zorder=3)
            ax.text(y, x, str(int(num)), color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
    if logo:
        ax_image = ax.inset_axes([0.02, 0.88, 0.12, 0.12], transform=ax.transAxes)
        ax_image.imshow(logo)
        ax_image.axis('off')
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    if not analysis_package:
        st.error("Ingen data modtaget.")
        return

    df_remote = analysis_package.get("remote_shapes", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_matches = analysis_package.get("matches", pd.DataFrame())

    if df_remote.empty:
        st.warning("Ingen positionsdata fundet.")
        return

    # --- DEBUG SECTION (FJERN NÅR DET VIRKER) ---
    # st.write("UUIDs i data:", df_remote['CONTESTANT_OPTAUUID'].unique().tolist())

    # --- DEN ULTIMATIVE MATCHER ---
    uuids_i_data = df_remote['CONTESTANT_OPTAUUID'].unique().tolist()
    team_map = {} 

    # Vi løber igennem alle UUIDs fundet i databasen
    for i, u_raw in enumerate(uuids_i_data):
        u_clean = str(u_raw).strip().lower()
        match_found = False
        
        # Tjek mod din team_mapping.py
        for t_name, t_info in TEAMS.items():
            # Vi tjekker både 'opta_uuid' og 'opta_id'
            m_uuid = str(t_info.get('opta_uuid', '')).strip().lower()
            if m_uuid and (m_uuid[:8] in u_clean or u_clean[:8] in m_uuid):
                team_map[t_name] = u_raw
                match_found = True
                break
        
        # Hvis intet match i mapping, kig i matches-tabellen
        if not match_found and not df_matches.empty:
            if i == 0:
                name = df_matches['CONTESTANTHOME_NAME'].iloc[0]
                team_map[name] = u_raw
            else:
                name = df_matches['CONTESTANTAWAY_NAME'].iloc[0]
                team_map[name] = u_raw

    # Hvis menuen stadig er tom, så vis rå ID'er så vi ikke dør helt
    if not team_map:
        team_map = {str(u): u for u in uuids_i_data}

    # UI
    valgt_hold = st.selectbox("Vælg hold:", sorted(list(team_map.keys())))
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)
    
    # ID til events
    event_uuid_ref = str(valgt_uuid_data).lower()[:8]

    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    with tabs[0]:
        df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'] == valgt_uuid_data]
        formation = df_h['SHAPE_FORMATION'].iloc[-1] if 'SHAPE_FORMATION' in df_h.columns else "N/A"
        st.subheader(f"{valgt_hold} ({formation})")
        
        # Beregn gennemsnit
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

        c1, c2 = st.columns(2)
        with c1:
            st.caption("🔴 **OFFENSIV**")
            draw_average_pitch(get_avg(df_h, 'inPossession'), t_color, t_logo)
        with c2:
            st.caption("⚪ **DEFENSIV**")
            draw_average_pitch(get_avg(df_h, 'outOfPossession'), "#333333", t_logo)

    # --- TABS FOR HEATMAPS & TOP 5 ---
    with tabs[1]: # MED BOLD
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if not df_h_ev.empty:
                pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
                cols = st.columns(2)
                for col, title, x_lim in zip(cols, ["OPBYGNING", "AFSLUTNING"], [(0,50), (50,100)]):
                    with col:
                        st.write(f"**{title}**")
                        fig, ax = pitch.draw(figsize=(4,5))
                        ax.set_ylim(x_lim[0], x_lim[1])
                        df_z = df_h_ev[(df_h_ev['EVENT_TYPEID']==1) & (df_h_ev['LOCATIONX'].between(x_lim[0], x_lim[1]))]
                        if not df_z.empty:
                            sns.kdeplot(x=df_z['LOCATIONY'], y=df_z['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax, bw_adjust=0.8)
                        st.pyplot(fig); plt.close(fig)
            else: st.info("Ingen hændelses-data fundet.")

    with tabs[3]: # TOP 5
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            c1, c2, c3 = st.columns(3)
            for col, (ids, label) in zip([c1, c2, c3], [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]):
                with col:
                    st.subheader(label)
                    stats = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(ids)]['PLAYER_NAME'].value_counts().head(5)
                    for n, v in stats.items(): st.write(f"**{v}** {n}")
