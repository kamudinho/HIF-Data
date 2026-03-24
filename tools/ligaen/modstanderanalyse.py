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

# --- 2. FORBEDRET MAPPING AF HOLD ---
def build_team_map(df_matches):
    # Vi fjerner COMP-filteret midlertidigt for at se om data overhovedet findes
    team_map = {}
    if df_matches.empty:
        return team_map
        
    for _, row in df_matches.iterrows():
        # Home
        h_name = row['CONTESTANTHOME_NAME']
        h_uuid = str(row['CONTESTANTHOME_OPTAUUID']).lower().strip()
        if h_name: team_map[h_name] = h_uuid
        
        # Away
        a_name = row['CONTESTANTAWAY_NAME']
        a_uuid = str(row['CONTESTANTAWAY_OPTAUUID']).lower().strip()
        if a_name: team_map[a_name] = a_uuid
            
    return team_map

def vis_side(analysis_package=None):
    if not analysis_package:
        st.error("Ingen data fundet.")
        return

    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_matches = analysis_package.get("matches", pd.DataFrame())

    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # 1. Byg mappet (Vi fjerner COMP-filteret for at sikre, at vi ser alle hold i pakken)
    team_map = build_team_map(None, df_matches)
    valgte_hold_liste = sorted(list(team_map.keys()))
    
    if not valgte_hold_liste:
        st.warning("Ingen hold fundet.")
        return

    valgt_hold = st.selectbox("Vælg hold:", valgte_hold_liste, label_visibility="collapsed")
    
    # 2. Definer variabler med den "tilgivende" logik
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)
    
    # Denne linje er nøglen: Vi renser UUID'et fuldstændigt
    event_uuid_ref = str(valgt_uuid_data).lower().replace('t', '').strip()
    # Vi tager de første 8 karakterer for at matche på tværs af kilder
    match_ref = event_uuid_ref[:8] 

    # 3. Definer tabs og pitch
    tabs = st.tabs(["MED BOLD", "MOD BOLD", "TOP 5"])
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', linewidth=1)

    # Filtrering - Vi tjekker om den rensede ref findes i data
    if not df_events.empty:
        df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(match_ref, na=False)].copy()
        
        if df_h_ev.empty:
            st.info(f"Ingen data fundet for {valgt_hold} i denne periode.")
            return

        # --- TAB 1: MED BOLD ---
        with tabs[0]:
            fokus = st.radio("Fokus:", ["Opbygning", "Gennembrud"], horizontal=True)
            c1, c2 = st.columns(2)
            if fokus == "Opbygning":
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
                with c2:
                    st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>PROGRESSIVE</p>", unsafe_allow_html=True)
                    if 'ENDLOCATIONX' in df_h_ev.columns:
                        df_prog = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['ENDLOCATIONX'] > (df_h_ev['LOCATIONX'] + 15))]
                        fig, ax = pitch.draw(figsize=(4, 5))
                        ax.set_ylim(40, 100)
                        if not df_prog.empty:
                            pitch.arrows(df_prog.LOCATIONX, df_prog.LOCATIONY, df_prog.ENDLOCATIONX, df_prog.ENDLOCATIONY, width=1.5, color=t_color, ax=ax, alpha=0.5)
                        draw_logo_on_ax(ax, t_logo)
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)

        # --- TAB 2: MOD BOLD ---
        with tabs[1]:
            c1, c2 = st.columns(2)
            for col, (etype, title, cmap) in zip([c1, c2], [([4, 8, 49], "EROBRINGER", "Blues"), ([5], "DUELLER", "Greens")]):
                with col:
                    st.write(f"<p style='text-align:center; font-size:11px; font-weight:bold;'>{title}</p>", unsafe_allow_html=True)
                    fig, ax = pitch.draw(figsize=(3, 4))
                    df_d = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(etype)]
                    if not df_d.empty:
                        sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], fill=True, cmap=cmap, alpha=0.5, ax=ax, bw_adjust=0.8)
                    draw_logo_on_ax(ax, t_logo)
                    st.pyplot(fig, use_container_width=True)
                    plt.close(fig)

        # --- TAB 3: TOP 5 ---
        with tabs[2]:
            c1, c2, c3 = st.columns(3)
            metrics = [([1], 'Afleveringer'), ([5], 'Dueller'), ([8, 49], 'Erobringer')]
            for col, (ids, label) in zip([c1, c2, c3], metrics):
                with col:
                    st.write(f"**{label}**")
                    stats = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(ids)]['PLAYER_NAME'].value_counts().head(5)
                    for n, v in stats.items(): st.write(f"{v} {n}")
