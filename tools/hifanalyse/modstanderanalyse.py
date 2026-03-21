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
            ax.scatter(y, x, s=400, color=color, edgecolors='black', linewidth=1.2, alpha=0.9, zorder=3)
            ax.text(y, x, str(int(num)), color='white', ha='center', va='center', 
                    fontsize=8, fontweight='bold', zorder=4)
            
    draw_logo_on_ax(ax, logo)
    
    # use_container_width=False gør at de ikke strækker sig til at fylde alt
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    st.markdown("<style>.block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)

    if not analysis_package:
        st.error("Ingen data fundet i analysis_package.")
        return

    # 1. HENT DATA (Dette skal ske FØR du bruger variablerne)
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_remote_raw = analysis_package.get("remote_shapes", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())

    # Nu kan du lave dit tjek uden fejl
    if not df_remote_raw.empty:
        # Vi printer det kun i konsollen/debug for ikke at forstyrre UI for meget
        unique_uuids_in_sql = df_remote_raw['CONTESTANT_OPTAUUID'].unique()
    else:
        unique_uuids_in_sql = []

    # 2. PARSING
    processed_rows = []
    if not df_remote_raw.empty:
        for _, row in df_remote_raw.iterrows():
            processed_rows.append({
                'CONTESTANT_OPTAUUID': str(row.get('CONTESTANT_OPTAUUID', '')).strip().lower(),
                'SHAPE_FORMATION': str(row.get('SHAPE_FORMATION', 'N/A')),
                'SHAPE_ROLE': row.get('SHAPE_ROLE', '[]'),
                'POSSESSION_TYPE': str(row.get('POSSESSION_TYPE', '')),
                'SHAPE_TIMEELAPSEDSTART': int(row.get('SHAPE_TIMEELAPSEDSTART', 0)) if str(row.get('SHAPE_TIMEELAPSEDSTART')) != 'nan' else 0
            })
    df_remote = pd.DataFrame(processed_rows)

    # 3. HOLDVALG
    all_teams = sorted(list(set(df_matches['CONTESTANTHOME_NAME']) | set(df_matches['CONTESTANTAWAY_NAME']))) if not df_matches.empty else []
    if not all_teams: 
        st.warning("Ingen hold fundet i matches data.")
        return
    
    valgt_hold = st.selectbox("Vælg hold:", all_teams)
    t_color, t_logo = get_team_style(valgt_hold)

    # Find UUID
    hold_uuid = ""
    m_row = df_matches[(df_matches['CONTESTANTHOME_NAME'] == valgt_hold) | (df_matches['CONTESTANTAWAY_NAME'] == valgt_hold)]
    if not m_row.empty:
        h_col = 'CONTESTANTHOME_OPTAUUID' if m_row['CONTESTANTHOME_NAME'].iloc[0] == valgt_hold else 'CONTESTANTAWAY_OPTAUUID'
        hold_uuid = str(m_row[h_col].iloc[0]).strip().lower()

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
        if not df_remote.empty and hold_uuid:
            # 1. Find alle rækker for holdet
            df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'].str.contains(hold_uuid[:15], na=False)]
            
            if not df_h.empty:
                st.subheader(f"Gennemsnitlig struktur: {valgt_hold}")
                
                c1, c2 = st.columns(2)
                
                # Beregn gennemsnit for de to faser
                avg_in = get_average_shape(df_h, 'inPossession')
                avg_out = get_average_shape(df_h, 'outOfPossession')
                
                with c1:
                    # Vi skal tilrette draw_remote_pitch til at modtage en DataFrame i stedet for en Row
                    st.write("**MED BOLD (In Possession)**")
                    draw_average_pitch(avg_in, t_color, t_logo)
                    
                with c2:
                    st.write("**UDEN BOLD (Out of Possession)**")
                    draw_average_pitch(avg_out, "#333333", t_logo)
            else:
                st.error("Ingen data fundet for dette hold.")
            
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
