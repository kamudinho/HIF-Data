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
    # Filtrér til NordicBet Liga (328)
    if 'COMPETITION_WYID' in df_matches.columns:
        df_matches = df_matches[df_matches['COMPETITION_WYID'] == 328]
    
    team_map = {}
    # Vi bruger navnene direkte fra kampsættet for at sikre 1:1 match med data
    for _, row in df_matches.iterrows():
        # Home team
        h_name = row['CONTESTANTHOME_NAME']
        h_uuid = str(row['CONTESTANTHOME_OPTAUUID']).lower().replace('t', '')
        if h_name not in team_map: team_map[h_name] = h_uuid
        
        # Away team
        a_name = row['CONTESTANTAWAY_NAME']
        a_uuid = str(row['CONTESTANTAWAY_OPTAUUID']).lower().replace('t', '')
        if a_name not in team_map: team_map[a_name] = a_uuid
            
    return team_map

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    if not analysis_package:
        st.error("Ingen data fundet.")
        return

    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_matches = analysis_package.get("matches", pd.DataFrame())

    if df_matches.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # Byg mappet og sorter listen
    team_map = build_team_map(df_matches)
    valgte_hold_liste = sorted(list(team_map.keys()))
    
    if not valgte_hold_liste:
        st.warning("Ingen hold fundet for NordicBet Ligaen.")
        return

    # Dropdown menu
    valgt_hold = st.selectbox("Vælg hold:", valgte_hold_liste, label_visibility="collapsed")
    
    # Hent stil og reference-ID (clean uuid uden 't')
    target_uuid = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)

    # Tabs og banekonfiguration
    tabs = st.tabs(["MED BOLD", "MOD BOLD", "TOP 5"])
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', linewidth=1)

    # Præ-filtrering af events for det valgte hold
    df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(target_uuid, na=False)].copy()

    if df_h_ev.empty:
        st.info(f"Ingen kamp-events fundet for {valgt_hold}.")
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
                if not df_kick.empty:
                    sns.kdeplot(x=df_kick['LOCATIONY'], y=df_kick['LOCATIONX'], fill=True, cmap='Reds', alpha=0.6, ax=ax, bw_adjust=0.8)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

            with c2:
                st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>OPBYGNING</p>", unsafe_allow_html=True)
                df_build = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'].between(15, 50))]
                fig, ax = pitch.draw(figsize=(4, 5))
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
                if not df_final.empty:
                    sns.kdeplot(x=df_final['LOCATIONY'], y=df_final['LOCATIONX'], fill=True, cmap='Oranges', alpha=0.6, ax=ax, bw_adjust=0.8)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

            with c2:
                st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>PROGRESSIVE AFLEVERINGER</p>", unsafe_allow_html=True)
                # Filter for afleveringer der flytter bolden mindst 15m fremad
                df_prog = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['ENDLOCATIONX'] > (df_h_ev['LOCATIONX'] + 15))]
                fig, ax = pitch.draw(figsize=(4, 5))
                if not df_prog.empty:
                    pitch.arrows(df_prog.LOCATIONX, df_prog.LOCATIONY, df_prog.ENDLOCATIONX, df_prog.ENDLOCATIONY, 
                                 width=1.5, color=t_color, ax=ax, alpha=0.5)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

    # --- TAB 2: MOD BOLD ---
    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>EROBRINGER</p>", unsafe_allow_html=True)
            df_def = df_h_ev[df_h_ev['EVENT_TYPEID'].isin([4, 8, 49])]
            fig, ax = pitch.draw(figsize=(4, 5))
            if not df_def.empty:
                sns.kdeplot(x=df_def['LOCATIONY'], y=df_def['LOCATIONX'], fill=True, cmap='Blues', alpha=0.5, ax=ax)
            draw_logo_on_ax(ax, t_logo)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        
        with c2:
            st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>DUELLER</p>", unsafe_allow_html=True)
            df_duel = df_h_ev[df_h_ev['EVENT_TYPEID'] == 5]
            fig, ax = pitch.draw(figsize=(4, 5))
            if not df_duel.empty:
                sns.kdeplot(x=df_duel['LOCATIONY'], y=df_duel['LOCATIONX'], fill=True, cmap='Greens', alpha=0.5, ax=ax)
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
                for name, val in stats.items():
                    st.write(f"{val} {name}")
