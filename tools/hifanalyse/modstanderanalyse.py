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

# --- 2. DEN NYE "MASTER MATCHER" LOGIK ---
def get_clean_map(df_remote, df_matches):
    uuids_i_data = df_remote['CONTESTANT_OPTAUUID'].unique().tolist()
    final_map = {} # Navn -> UUID fra data
    
    # Hent officielle navne fra kamp-dataen som backup
    h_name_official = df_matches['CONTESTANTHOME_NAME'].iloc[0] if not df_matches.empty else "Hjemmehold"
    a_name_official = df_matches['CONTESTANTAWAY_NAME'].iloc[0] if not df_matches.empty else "Udehold"
    
    for i, u_raw in enumerate(uuids_i_data):
        u_clean = str(u_raw).strip().lower()
        found_name = None
        
        # PRIORITET 1: Tjek opta_uuid i din mapping (Fuzzy match)
        for t_name, t_info in TEAMS.items():
            mapped_uuid = str(t_info.get('opta_uuid', '')).strip().lower()
            if mapped_uuid and (mapped_uuid[:8] in u_clean or u_clean[:8] in mapped_uuid):
                found_name = t_name
                break
        
        # PRIORITET 2: Hvis ikke fundet, brug navnet fra kamp-tabellen (Home/Away rækkefølge)
        if not found_name:
            if i == 0: found_name = h_name_official
            else: found_name = a_name_official
            
        final_map[found_name] = u_raw
        
    return final_map

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

    # Kør den forbedrede mapping
    team_map = get_clean_map(df_remote, df_matches)
    
    # UI - Vælg hold
    valgt_hold = st.selectbox("Vælg hold:", sorted(list(team_map.keys())))
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)
    
    # Nøgle til hændelser (bruger de første 8 tegn af det ID vi har i dataen)
    event_uuid_ref = str(valgt_uuid_data).lower()[:8]

    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # --- TAB 0: STRUKTUR ---
    with tabs[0]:
        df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'] == valgt_uuid_data]
        formation = df_h['SHAPE_FORMATION'].iloc[-1] if 'SHAPE_FORMATION' in df_h.columns else "N/A"
        st.subheader(f"{valgt_hold} - Formation: {formation}")
        
        # Hjælpefunktion til gennemsnitspositioner
        def get_avg(df, phase):
            df_f = df[df['POSSESSION_TYPE'].str.contains(phase, case=False, na=False)]
            all_p = []
            for r in df_f['SHAPE_ROLE']:
                roles = json.loads(r) if isinstance(r, str) else r
                if isinstance(roles, list): all_p.extend(roles)
            if not all_p: return pd.DataFrame()
            df_p = pd.DataFrame(all_p)
            df_p[['averageRolePositionX', 'averageRolePositionY']] = df_p[['averageRolePositionX', 'averageRolePositionY']].apply(pd.to_numeric)
            return df_p.groupby('shirtNumber').agg({'averageRolePositionX':'mean', 'averageRolePositionY':'mean'}).reset_index()

        avg_in = get_avg(df_h, 'inPossession')
        avg_out = get_avg(df_h, 'outOfPossession')
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption("🔴 **OFFENSIV**")
            draw_average_pitch(avg_in, t_color, t_logo)
        with c2:
            st.caption("⚪ **DEFENSIV**")
            draw_average_pitch(avg_out, "#333333", t_logo)

    # --- TAB 1 & 2: HEATMAPS (Nu med fejlsikret ID) ---
    with tabs[1]: # MED BOLD
        if not df_events.empty:
            # Vi filtrerer df_events ved at kigge efter vores event_uuid_ref
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if df_h_ev.empty:
                # Hvis vi ikke finder noget, prøver vi at matche på PLAYER_NAME for at se om data overhovedet er der
                st.warning(f"Kunne ikke finde hændelser for ID: {event_uuid_ref}")
            else:
                pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
                # ... (Her indsættes din eksisterende heatmap-tegning) ...
                st.success(f"Viser hændelser for {valgt_hold}")import streamlit as st
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

# --- 2. DEN NYE "MASTER MATCHER" LOGIK ---
def get_clean_map(df_remote, df_matches):
    uuids_i_data = df_remote['CONTESTANT_OPTAUUID'].unique().tolist()
    final_map = {} # Navn -> UUID fra data
    
    # Hent officielle navne fra kamp-dataen som backup
    h_name_official = df_matches['CONTESTANTHOME_NAME'].iloc[0] if not df_matches.empty else "Hjemmehold"
    a_name_official = df_matches['CONTESTANTAWAY_NAME'].iloc[0] if not df_matches.empty else "Udehold"
    
    for i, u_raw in enumerate(uuids_i_data):
        u_clean = str(u_raw).strip().lower()
        found_name = None
        
        # PRIORITET 1: Tjek opta_uuid i din mapping (Fuzzy match)
        for t_name, t_info in TEAMS.items():
            mapped_uuid = str(t_info.get('opta_uuid', '')).strip().lower()
            if mapped_uuid and (mapped_uuid[:8] in u_clean or u_clean[:8] in mapped_uuid):
                found_name = t_name
                break
        
        # PRIORITET 2: Hvis ikke fundet, brug navnet fra kamp-tabellen (Home/Away rækkefølge)
        if not found_name:
            if i == 0: found_name = h_name_official
            else: found_name = a_name_official
            
        final_map[found_name] = u_raw
        
    return final_map

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

    # Kør den forbedrede mapping
    team_map = get_clean_map(df_remote, df_matches)
    
    # UI - Vælg hold
    valgt_hold = st.selectbox("Vælg hold:", sorted(list(team_map.keys())))
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)
    
    # Nøgle til hændelser (bruger de første 8 tegn af det ID vi har i dataen)
    event_uuid_ref = str(valgt_uuid_data).lower()[:8]

    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # --- TAB 0: STRUKTUR ---
    with tabs[0]:
        df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'] == valgt_uuid_data]
        formation = df_h['SHAPE_FORMATION'].iloc[-1] if 'SHAPE_FORMATION' in df_h.columns else "N/A"
        st.subheader(f"{valgt_hold} - Formation: {formation}")
        
        # Hjælpefunktion til gennemsnitspositioner
        def get_avg(df, phase):
            df_f = df[df['POSSESSION_TYPE'].str.contains(phase, case=False, na=False)]
            all_p = []
            for r in df_f['SHAPE_ROLE']:
                roles = json.loads(r) if isinstance(r, str) else r
                if isinstance(roles, list): all_p.extend(roles)
            if not all_p: return pd.DataFrame()
            df_p = pd.DataFrame(all_p)
            df_p[['averageRolePositionX', 'averageRolePositionY']] = df_p[['averageRolePositionX', 'averageRolePositionY']].apply(pd.to_numeric)
            return df_p.groupby('shirtNumber').agg({'averageRolePositionX':'mean', 'averageRolePositionY':'mean'}).reset_index()

        avg_in = get_avg(df_h, 'inPossession')
        avg_out = get_avg(df_h, 'outOfPossession')
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption("🔴 **OFFENSIV**")
            draw_average_pitch(avg_in, t_color, t_logo)
        with c2:
            st.caption("⚪ **DEFENSIV**")
            draw_average_pitch(avg_out, "#333333", t_logo)

    # --- TAB 1 & 2: HEATMAPS (Nu med fejlsikret ID) ---
    with tabs[1]: # MED BOLD
        if not df_events.empty:
            # Vi filtrerer df_events ved at kigge efter vores event_uuid_ref
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if df_h_ev.empty:
                # Hvis vi ikke finder noget, prøver vi at matche på PLAYER_NAME for at se om data overhovedet er der
                st.warning(f"Kunne ikke finde hændelser for ID: {event_uuid_ref}")
            else:
                pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
                # ... (Her indsættes din eksisterende heatmap-tegning) ...
                st.success(f"Viser hændelser for {valgt_hold}")
