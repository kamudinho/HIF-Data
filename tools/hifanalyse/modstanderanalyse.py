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
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- 1. LOGO & FARVE HJÆLPEFUNKTIONER ---
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

# --- 2. TEGNEFUNKTION TIL STRUKTUR ---
def draw_average_pitch(df_avg, color, logo):
    # Mindre figsize (bredde, højde) for at undgå scrolling
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', line_zorder=2)
    fig, ax = pitch.draw(figsize=(4, 5)) 
    
    if not df_avg.empty:
        for _, row in df_avg.iterrows():
            x = row['averageRolePositionX']
            y = row['averageRolePositionY']
            num = row['shirtNumber']
            
            # Lidt mindre prikker (s=400) passer bedre til en mindre bane
            ax.scatter(y, x, s=200, color=color, edgecolors='black', linewidth=0.7, alpha=0.9, zorder=3)
            ax.text(y, x, str(int(num)), color='white', ha='center', va='center', 
                    fontsize=6, fontweight='bold', zorder=4)
            
    draw_logo_on_ax(ax, logo)
    
    # use_container_width=False gør at de ikke strækker sig til at fylde alt
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    # 1. HENT DATA
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_remote_raw = analysis_package.get("remote_shapes", pd.DataFrame())

    if df_remote_raw.empty:
        st.warning("Ingen positions-data (remote_shapes) fundet.")
        return

    # 2. FIND DE TO HOLD I DATAEN
    # Vi finder de unikke UUIDs der er i denne kamps shapes
    uuids_i_data = df_remote_raw['CONTESTANT_OPTAUUID'].unique().tolist()
    
    # Lav en ordbog der mapper UUID -> Navn baseret på matches-tabellen
    team_map = {}
    for _, m in df_matches.iterrows():
        team_map[str(m['CONTESTANTHOME_OPTAUUID']).strip().lower()] = m['CONTESTANTHOME_NAME']
        team_map[str(m['CONTESTANTAWAY_OPTAUUID']).strip().lower()] = m['CONTESTANTAWAY_NAME']

    # Lav en liste over holdnavne vi rent faktisk har data på
    holds_navne = []
    uuid_to_name = {}
    for u in uuids_i_data:
        u_clean = str(u).strip().lower()
        # Vi tjekker om de første 10 tegn matcher (for at undgå UUID-format fejl)
        found = False
        for m_uuid, m_name in team_map.items():
            if u_clean[:10] in m_uuid or m_uuid[:10] in u_clean:
                holds_navne.append(m_name)
                uuid_to_name[m_name] = u
                found = True
                break
    
    if not holds_navne:
        st.error("Kunne ikke matche holdnavne med UUIDs i data.")
        st.write("UUIDs i data:", uuids_i_data)
        return

    def vis_side(analysis_package=None):
    # 1. HENT DATA
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_remote_raw = analysis_package.get("remote_shapes", pd.DataFrame())

    if df_remote_raw.empty:
        st.warning("Ingen positions-data (remote_shapes) fundet.")
        return

    # 2. FIND DE TO HOLD I DATAEN
    # Vi finder de unikke UUIDs der er i denne kamps shapes
    uuids_i_data = df_remote_raw['CONTESTANT_OPTAUUID'].unique().tolist()
    
    # Lav en ordbog der mapper UUID -> Navn baseret på matches-tabellen
    team_map = {}
    for _, m in df_matches.iterrows():
        team_map[str(m['CONTESTANTHOME_OPTAUUID']).strip().lower()] = m['CONTESTANTHOME_NAME']
        team_map[str(m['CONTESTANTAWAY_OPTAUUID']).strip().lower()] = m['CONTESTANTAWAY_NAME']

    # Lav en liste over holdnavne vi rent faktisk har data på
    holds_navne = []
    uuid_to_name = {}
    for u in uuids_i_data:
        u_clean = str(u).strip().lower()
        # Vi tjekker om de første 10 tegn matcher (for at undgå UUID-format fejl)
        found = False
        for m_uuid, m_name in team_map.items():
            if u_clean[:10] in m_uuid or m_uuid[:10] in u_clean:
                holds_navne.append(m_name)
                uuid_to_name[m_name] = u
                found = True
                break
    
    if not holds_navne:
        st.error("Kunne ikke matche holdnavne med UUIDs i data.")
        st.write("UUIDs i data:", uuids_i_data)
        return

    # 3. BRUGERVALG
    valgt_hold = st.selectbox("Vælg hold fra kampen:", sorted(list(set(holds_navne))))
    t_color, t_logo = get_team_style(valgt_hold)
    valgt_uuid = uuid_to_name[valgt_hold]

    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # --- NY HJÆLPEFUNKTION TIL GENNEMSNIT ---
    def get_average_shape(df_hold, possession_type):
        # Filtrer på fase
        df_fase = df_hold[df_hold['POSSESSION_TYPE'].str.contains(possession_type, case=False)]
        
        all_players = []
        for _, row in df_fase.iterrows():
            roles_raw = row.get('SHAPE_ROLE', [])
            roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw
            if isinstance(roles, list):
                for r in roles:
                    all_players.append(r)
        
        if not all_players:
            return pd.DataFrame()
            
        df_p = pd.DataFrame(all_players)
        
        # --- FIX: Konverter koordinater til tal før aggregering ---
        df_p['averageRolePositionX'] = pd.to_numeric(df_p['averageRolePositionX'], errors='coerce')
        df_p['averageRolePositionY'] = pd.to_numeric(df_p['averageRolePositionY'], errors='coerce')
        
        # Grupper på spillernummer
        df_avg = df_p.groupby('shirtNumber').agg({
            'averageRolePositionX': 'mean',
            'averageRolePositionY': 'mean',
            'roleDescription': 'first'
        }).reset_index()
        
        return df_avg
    
    # --- OPDATERET DEL AF tabs[0] ---
    with tabs[0]:
        # Filtrer data baseret på den UUID vi VED findes
        df_h = df_remote_raw[df_remote_raw['CONTESTANT_OPTAUUID'] == valgt_uuid]
        
        if not df_h.empty:
            avg_in = get_average_shape(df_h, 'inPossession')
            avg_out = get_average_shape(df_h, 'outOfPossession')
            
            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"🔴 **{valgt_hold} OFFENSIV**")
                draw_average_pitch(avg_in, t_color, t_logo)
            with c2:
                st.caption(f"⚪ **{valgt_hold} DEFENSIV**")
                draw_average_pitch(avg_out, "#333333", t_logo)
            else:
                # --- DEBUG HJÆLP ---
                st.error(f"Ingen data fundet i Remote Shapes for {valgt_hold}")
                with st.expander("Klik for at se hvorfor (Debug)"):
                    st.write(f"Søger efter UUID: `{target_uuid}`")
                    st.write("UUIDs der findes i databasen:")
                    st.write(df_remote['CONTESTANT_OPTAUUID'].unique()[:5])
        else:
            st.warning("Data mangler eller hold UUID kunne ikke findes.")
            
    with tabs[1]: # MED BOLD (Heatmaps)
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            for col, title, x_range in zip([c1, c2], ["OPBYGNING", "AFSLUTNING"], [(0, 50), (50, 100)]):
                with col:
                    st.write(f"**{title}**")
                    fig, ax = pitch_h.draw(figsize=(6, 8))
                    ax.set_ylim(x_range[0], x_range[1])
                    df_z = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'] >= x_range[0]) & (df_h_ev['LOCATIONX'] < x_range[1])]
                    if not df_z.empty:
                        sns.kdeplot(x=df_z['LOCATIONY'], y=df_z['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax)
                    draw_logo_on_ax(ax, t_logo)
                    st.pyplot(fig); plt.close(fig)
        else: st.info("Ingen hændelsesdata (events) fundet.")

    with tabs[2]: # MOD BOLD
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            c1, c2 = st.columns(2)
            for col, (etype, title, cmap) in zip([c1, c2], [([4, 8, 49], "EROBRINGER", "Blues"), ([5], "DUELLER", "Greens")]):
                with col:
                    st.write(f"**{title}**")
                    fig, ax = pitch.draw(figsize=(5, 7))
                    df_d = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(etype)]
                    if not df_d.empty:
                        sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], fill=True, cmap=cmap, alpha=0.5, ax=ax)
                    draw_logo_on_ax(ax, t_logo); st.pyplot(fig); plt.close(fig)

    with tabs[3]: # TOP 5
        if not df_events.empty and hold_uuid:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(hold_uuid[:15], na=False)]
            cols = st.columns(3)
            metrics = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
            for i, (tid, nav) in enumerate(metrics):
                with cols[i]:
                    st.subheader(nav)
                    top = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(tid)]['PLAYER_NAME'].value_counts().head(5)
                    for name, val in top.items():
                        st.markdown(f"**{val}** {name}")
