import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import requests
from io import BytesIO
from PIL import Image

# --- 1. HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(url):
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def get_team_style(team_name):
    from data.utils.team_mapping import TEAMS, TEAM_COLORS
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
    from data.utils.team_mapping import TEAMS
    # Vi kigger på alle unikke hold i de hentede kampe (allerede filtreret på sæson i din SQL)
    ids_i_ligaen = pd.concat([
        df_matches['CONTESTANTHOME_OPTAUUID'], 
        df_matches['CONTESTANTAWAY_OPTAUUID']
    ]).unique()
    
    team_map = {}
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().strip(): name for name, info in TEAMS.items()}
    
    for u_raw in ids_i_ligaen:
        if pd.isna(u_raw): continue
        u_clean = str(u_raw).lower().strip()
        matched_name = mapping_lookup.get(u_clean)
        
        if not matched_name:
            # Fallback til navnet direkte fra databasen hvis ikke i TEAMS mapping
            match_row = df_matches[df_matches['CONTESTANTHOME_OPTAUUID'] == u_raw]
            if not match_row.empty:
                matched_name = match_row['CONTESTANTHOME_NAME'].iloc[0]
            else:
                match_away = df_matches[df_matches['CONTESTANTAWAY_OPTAUUID'] == u_raw]
                if not match_away.empty:
                    matched_name = match_away['CONTESTANTAWAY_NAME'].iloc[0]

        if matched_name:
            team_map[matched_name] = u_raw
            
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

    # 1. Byg mappet og vælg hold
    team_map = build_team_map(df_matches)
    valgte_hold_liste = sorted(list(team_map.keys()))
    
    col_header1, col_header2 = st.columns([2, 2])
    with col_header1:
        valgt_hold = st.selectbox("Vælg hold:", valgte_hold_liste)
    
    valgt_uuid = str(team_map[valgt_hold]).lower().strip()
    t_color, t_logo = get_team_style(valgt_hold)

    # 2. Håndtering af kampspecifik filtrering uden MATCH_DESCRIPTION
    holdets_kampe = df_matches[
        (df_matches['CONTESTANTHOME_OPTAUUID'].str.lower() == valgt_uuid) | 
        (df_matches['CONTESTANTAWAY_OPTAUUID'].str.lower() == valgt_uuid)
    ].copy()

    if not holdets_kampe.empty:
        # Vi opretter KAMP_NAVN manuelt for at undgå KeyError
        holdets_kampe['KAMP_NAVN'] = holdets_kampe['CONTESTANTHOME_NAME'] + " - " + holdets_kampe['CONTESTANTAWAY_NAME']
    
    with col_header2:
        kamp_optioner = ["Hele sæsonen"] 
        if not holdets_kampe.empty:
            kamp_optioner += holdets_kampe['KAMP_NAVN'].tolist()
        
        valgt_kamp = st.selectbox("Vælg periode/kamp:", kamp_optioner)

    # 3. Filtrering af hændelser
    if valgt_kamp == "Hele sæsonen":
        df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower() == valgt_uuid].copy()
    else:
        m_uuid = holdets_kampe[holdets_kampe['KAMP_NAVN'] == valgt_kamp]['MATCH_OPTAUUID'].iloc[0]
        df_h_ev = df_events[
            (df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower() == valgt_uuid) & 
            (df_events['MATCH_OPTAUUID'] == m_uuid)
        ].copy()

    if df_h_ev.empty:
        st.info(f"Ingen hændelsesdata fundet for {valgt_hold}.")
        return

    # 4. Visualisering (Tabs og Pitch)
    tabs = st.tabs(["MED BOLD", "MOD BOLD", "TOP 5"])
    pitch = VerticalPitch(pitch_type='opta', pitch_color='white', line_color='#333333', linewidth=1)

    # TAB: MED BOLD
    with tabs[0]:
        fokus = st.radio("Fokus:", ["Opbygning", "Afslutninger"], horizontal=True)
        c1, c2 = st.columns(2)
        if fokus == "Opbygning":
            with c1:
                st.markdown("<p style='text-align:center; font-weight:bold;'>FASE 1: MÅLSPARK / LAV OPBYGNING</p>", unsafe_allow_html=True)
                df_f = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'] < 20)]
                fig, ax = pitch.draw(figsize=(4, 6))
                if not df_f.empty:
                    sns.kdeplot(x=df_f['LOCATIONY'], y=df_f['LOCATIONX'], fill=True, cmap='Reds', alpha=0.6, ax=ax, bw_adjust=0.8)
                ax.set_ylim(0, 55)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig); plt.close(fig)
            with c2:
                st.markdown("<p style='text-align:center; font-weight:bold;'>FASE 2: OPBYGNING</p>", unsafe_allow_html=True)
                df_f = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['LOCATIONX'].between(20, 60))]
                fig, ax = pitch.draw(figsize=(4, 6))
                if not df_f.empty:
                    sns.kdeplot(x=df_f['LOCATIONY'], y=df_f['LOCATIONX'], fill=True, cmap='Reds', alpha=0.6, ax=ax, bw_adjust=0.8)
                ax.set_ylim(0, 55)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig); plt.close(fig)
        else:
            with c1:
                st.markdown("<p style='text-align:center; font-weight:bold;'>FASE 3: GENNEMBRUDSZONER</p>", unsafe_allow_html=True)
                df_f = df_h_ev[df_h_ev['LOCATIONX'] > 66]
                fig, ax = pitch.draw(figsize=(4, 6))
                if not df_f.empty:
                    sns.kdeplot(x=df_f['LOCATIONY'], y=df_f['LOCATIONX'], fill=True, cmap='Oranges', alpha=0.6, ax=ax, bw_adjust=0.8)
                ax.set_ylim(45, 101)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig); plt.close(fig)
            with c2:
                st.markdown("<p style='text-align:center; font-weight:bold;'>FASE 4: AFSLUTNINGER</p>", unsafe_allow_html=True)
                df_shots = df_h_ev[df_h_ev['EVENT_TYPEID'].isin([13, 14, 15, 16])]
                fig, ax = pitch.draw(figsize=(4, 6))
                if not df_shots.empty:
                    goals = df_shots[df_shots['EVENT_TYPEID'] == 16]
                    non_goals = df_shots[df_shots['EVENT_TYPEID'] != 16]
                    pitch.scatter(non_goals.LOCATIONX, non_goals.LOCATIONY, s=30, edgecolors=t_color, c='white', alpha=0.6, ax=ax)
                    pitch.scatter(goals.LOCATIONX, goals.LOCATIONY, s=60, c=t_color, edgecolors='black', ax=ax, zorder=3)
                ax.set_ylim(45, 101)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig); plt.close(fig)

    # TAB: MOD BOLD
    with tabs[1]:
        c1, c2 = st.columns(2)
        for col, (etype, title, cmap) in zip([c1, c2], [([4, 8, 12, 49], "DEFENSIVE AKTIONER", "Blues"), ([5], "DUELLER", "Greens")]):
            with col:
                st.markdown(f"<p style='text-align:center; font-weight:bold;'>{title}</p>", unsafe_allow_html=True)
                fig, ax = pitch.draw(figsize=(4, 6))
                df_d = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(etype)]
                if not df_d.empty:
                    sns.kdeplot(x=df_d['LOCATIONY'], y=df_d['LOCATIONX'], fill=True, cmap=cmap, alpha=0.5, ax=ax, bw_adjust=0.8)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig); plt.close(fig)

    # TAB: TOP 5
    with tabs[2]:
        st.subheader(f"Top 5 Spillere - {valgt_kamp}")
        c1, c2, c3 = st.columns(3)
        metrics = [([1], 'Afleveringer'), ([5], 'Dueller'), ([4, 8, 49], 'Erobringer')]
        for col, (ids, label) in zip([c1, c2, c3], metrics):
            with col:
                st.write(f"**{label}**")
                stats = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(ids)]['PLAYER_NAME'].value_counts().head(5)
                if stats.empty:
                    st.write("Ingen data")
                else:
                    for n, v in stats.items(): 
                        st.write(f"**{v}** {n}")
