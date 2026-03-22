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

# --- 2. MASTER MATCHER (LØSNINGEN PÅ DIT PROBLEM) ---
def build_team_map(df_remote, df_matches):
    """
    Denne funktion sikrer, at alle UUIDs fra databasen bliver koblet til et navn.
    Den tjekker først din mapping-fil, og derefter matches-tabellen.
    """
    raw_uuids = df_remote['CONTESTANT_OPTAUUID'].unique().tolist()
    team_map = {}
    
    # Lav en lynhurtig oversigt over alle kendte hold-ID'er fra din mapping
    mapping_lookup = {str(info.get('opta_uuid', '')).lower()[:8]: name for name, info in TEAMS.items()}
    
    # Hent navne fra kampene i pakken
    db_teams = []
    if not df_matches.empty:
        # Samler alle unikke kombinationer af ID og Navn fra kamp-tabellen
        home = df_matches[['CONTESTANTHOME_OPTAUUID', 'CONTESTANTHOME_NAME']].rename(columns={'CONTESTANTHOME_OPTAUUID': 'id', 'CONTESTANTHOME_NAME': 'name'})
        away = df_matches[['CONTESTANTAWAY_OPTAUUID', 'CONTESTANTAWAY_NAME']].rename(columns={'CONTESTANTAWAY_OPTAUUID': 'id', 'CONTESTANTAWAY_NAME': 'name'})
        db_teams = pd.concat([home, away]).drop_duplicates()

    for u_raw in raw_uuids:
        u_clean = str(u_raw).lower().strip()
        matched_name = None
        
        # 1. Tjek mapping-filen (Fuzzy match)
        for m_id, name in mapping_lookup.items():
            if m_id and (m_id in u_clean or u_clean.startswith(m_id)):
                matched_name = name
                break
        
        # 2. Hvis ikke fundet, tjek kamp-tabellen (df_matches)
        if not matched_name and not db_teams.empty:
            match_row = db_teams[db_teams['id'].str.lower() == u_clean]
            if not match_row.empty:
                matched_name = match_row['name'].iloc[0]
        
        # 3. Sidste udvej: Brug de første 6 tegn af ID'et
        if not matched_name:
            matched_name = f"Ukendt ({u_clean[:6]})"
            
        team_map[matched_name] = u_raw
        
    return team_map

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    st.markdown("<style>.block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)
    
    if not analysis_package:
        st.error("Ingen data fundet.")
        return

    df_remote = analysis_package.get("remote_shapes", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_matches = analysis_package.get("matches", pd.DataFrame())

    if df_remote.empty:
        st.warning("Ingen positionsdata fundet.")
        return

    # Vis debug-info kun hvis nødvendigt
    # st.info(f"Debug: {df_remote['CONTESTANT_OPTAUUID'].unique().tolist()}")

    # Byg hold-oversigten
    team_map = build_team_map(df_remote, df_matches)
    
    valgt_hold = st.selectbox("Vælg hold:", sorted(list(team_map.keys())))
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)
    
    # Reference til hændelser
    event_uuid_ref = str(valgt_uuid_data).lower()[:8]

    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # --- STRUKTUR TAB ---
    with tabs[0]:
        df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'] == valgt_uuid_data]
        formation = df_h['SHAPE_FORMATION'].iloc[-1] if 'SHAPE_FORMATION' in df_h.columns else "N/A"
        st.subheader(f"{valgt_hold} - Formation: {formation}")
        
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

        avg_in = get_avg(df_h, 'inPossession')
        avg_out = get_avg(df_h, 'outOfPossession')
        
        pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
        c1, c2 = st.columns(2)
        
        for col, data, title, dot_color in zip([c1, c2], [avg_in, avg_out], ["OFFENSIV", "DEFENSIV"], [t_color, "#333333"]):
            with col:
                st.caption(f"● {title}")
                fig, ax = pitch.draw(figsize=(4, 5))
                if not data.empty:
                    for _, row in data.iterrows():
                        ax.scatter(row['averageRolePositionY'], row['averageRolePositionX'], s=250, color=dot_color, edgecolors='black', zorder=3)
                        ax.text(row['averageRolePositionY'], row['averageRolePositionX'], str(int(row['shirtNumber'])), color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
                draw_logo_on_ax(ax, t_logo); st.pyplot(fig); plt.close(fig)

    # --- TOP 5 TAB ---
    with tabs[3]:
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if df_h_ev.empty:
                st.warning("Ingen hændelser fundet for dette hold.")
            else:
                c1, c2, c3 = st.columns(3)
                metrics = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
                for col, (ids, label) in zip([c1, c2, c3], metrics):
                    with col:
                        st.subheader(label)
                        stats = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(ids)]['PLAYER_NAME'].value_counts().head(5)
                        for n, v in stats.items(): st.write(f"**{v}** {n}")
