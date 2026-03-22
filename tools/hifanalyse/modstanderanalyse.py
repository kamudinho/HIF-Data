import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import requests
from io import BytesIO
from PIL import Image
import json
import re

# --- 1. LOGO & FARVE HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(url):
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def get_team_style(team_name):
    # Standardfarve (Hvidovre rød)
    color = '#df003b' 
    logo_img = None
    
    # Prøv at hente fra dine mappings (Importeret i toppen af din fil normalt)
    try:
        from data.utils.team_mapping import TEAMS, TEAM_COLORS
        if team_name in TEAM_COLORS:
            c = TEAM_COLORS[team_name]
            prim = str(c.get('primary', '#df003b')).lower()
            color = c.get('secondary', '#333333') if prim in ["#ffffff", "white", "#f9f9f9"] else prim
        if team_name in TEAMS:
            url = TEAMS[team_name].get('logo')
            if url: logo_img = get_logo_img(url)
    except:
        pass
    return color, logo_img

def draw_logo_on_ax(ax, logo_img):
    if logo_img:
        try:
            ax_image = ax.inset_axes([0.02, 0.88, 0.12, 0.12], transform=ax.transAxes)
            ax_image.imshow(logo_img)
            ax_image.axis('off')
        except: pass

# --- 2. TEGNEFUNKTION TIL STRUKTUR ---
def draw_average_pitch(df_avg, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', line_zorder=2)
    fig, ax = pitch.draw(figsize=(4, 5)) 
    
    if df_avg is not None and not df_avg.empty:
        for _, row in df_avg.iterrows():
            x = row.get('averageRolePositionX', 0)
            y = row.get('averageRolePositionY', 0)
            num = row.get('shirtNumber', 0)
            
            ax.scatter(y, x, s=200, color=color, edgecolors='black', linewidth=0.7, alpha=0.9, zorder=3)
            ax.text(y, x, str(int(num)), color='white', ha='center', va='center', 
                    fontsize=6, fontweight='bold', zorder=4)
            
    draw_logo_on_ax(ax, logo)
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)

# --- 3. HJÆLPEFUNKTION TIL GENNEMSNIT ---
def get_average_shape(df_hold, possession_type):
    try:
        df_fase = df_hold[df_hold['POSSESSION_TYPE'].str.contains(possession_type, case=False, na=False)]
        all_players = []
        for _, row in df_fase.iterrows():
            roles_raw = row.get('SHAPE_ROLE', [])
            roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw
            if isinstance(roles, list):
                for r in roles:
                    all_players.append(r)
        
        if not all_players: return pd.DataFrame()
        
        df_p = pd.DataFrame(all_players)
        df_p['averageRolePositionX'] = pd.to_numeric(df_p['averageRolePositionX'], errors='coerce')
        df_p['averageRolePositionY'] = pd.to_numeric(df_p['averageRolePositionY'], errors='coerce')
        
        return df_p.groupby('shirtNumber').agg({
            'averageRolePositionX': 'mean', 'averageRolePositionY': 'mean', 'roleDescription': 'first'
        }).reset_index()
    except:
        return pd.DataFrame()

# --- 4. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    st.markdown("<style>.block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)

    if analysis_package is None:
        st.error("🚨 Fejl: 'analysis_package' er None. Tjek din data-indlæsning i hovedfilen.")
        return

    try:
        # 1. HENT DATA SIKKERT
        df_matches = analysis_package.get("matches", pd.DataFrame())
        df_remote_raw = analysis_package.get("remote_shapes", pd.DataFrame())
        df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())

        if df_remote_raw.empty:
            st.warning("⚠️ Ingen positions-data fundet i 'remote_shapes'.")
            return

        # 2. FIND DE TO HOLD
        uuids_i_data = df_remote_raw['CONTESTANT_OPTAUUID'].unique().tolist()
        
        # Hent navne fra matches hvis de findes
        h_name, a_name = "Hjemmehold", "Udehold"
        h_uuid_ref, a_uuid_ref = "", ""
        
        if not df_matches.empty:
            h_name = df_matches['CONTESTANTHOME_NAME'].iloc[0]
            a_name = df_matches['CONTESTANTAWAY_NAME'].iloc[0]
            h_uuid_ref = str(df_matches['CONTESTANTHOME_OPTAUUID'].iloc[0]).lower()
            a_uuid_ref = str(df_matches['CONTESTANTAWAY_OPTAUUID'].iloc[0]).lower()

        uuid_to_name = {}
        found_names = []

        for u in uuids_i_data:
            u_str = str(u).lower()
            if h_uuid_ref and (u_str[:8] in h_uuid_ref or h_uuid_ref[:8] in u_str):
                uuid_to_name[h_name] = u
                found_names.append(h_name)
            elif a_uuid_ref and (u_str[:8] in a_uuid_ref or a_uuid_ref[:8] in u_str):
                uuid_to_name[a_name] = u
                found_names.append(a_name)

        # NØDBREMSE
        if len(uuids_i_data) >= 2 and len(found_names) < 2:
            # Hvis vi har 2 ID'er men kun kender det ene navn, tildel det andet til modstanderen
            for u in uuids_i_data:
                if u not in uuid_to_name.values():
                    mangler = a_name if h_name in found_names else h_name
                    uuid_to_name[mangler] = u
                    found_names.append(mangler)
                    break
        
        if not found_names:
            st.error("Kunne ikke matche hold-navne med dataen.")
            st.write("UUIDs i database:", uuids_i_data)
            return

        # 3. UI
        valgt_hold = st.selectbox("Vælg hold:", sorted(list(set(found_names))))
        t_color, t_logo = get_team_style(valgt_hold)
        valgt_uuid = uuid_to_name[valgt_hold]

        tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

        with tabs[0]:
            df_h = df_remote_raw[df_remote_raw['CONTESTANT_OPTAUUID'] == valgt_uuid]
            avg_in = get_average_shape(df_h, 'inPossession')
            avg_out = get_average_shape(df_h, 'outOfPossession')
            
            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"🔴 **{valgt_hold} I BESIDDELSE**")
                draw_average_pitch(avg_in, t_color, t_logo)
            with c2:
                st.caption(f"⚪ **{valgt_hold} MOD BOLDEN**")
                draw_average_pitch(avg_out, "#333333", t_logo)

        # De andre tabs (Events)
        with tabs[1]:
            if not df_events.empty:
                event_uuid = str(valgt_uuid)[:10]
                df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid, na=False)]
                # ... Resten af din heatmap kode (den er stabil) ...
                st.info("Heatmaps indlæses her...")
            else: st.info("Ingen hændelsesdata fundet.")

    except Exception as e:
        st.error(f"Der skete en uventet fejl: {e}")
