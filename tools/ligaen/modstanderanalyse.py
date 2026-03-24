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
    # Filtrér til 1. division (NordicBet Liga = 328)
    if 'COMPETITION_WYID' in df_matches.columns:
        df_matches = df_matches[df_matches['COMPETITION_WYID'] == 328]
    
    ids_i_ligaen = pd.concat([
        df_matches['CONTESTANTHOME_OPTAUUID'], 
        df_matches['CONTESTANTAWAY_OPTAUUID']
    ]).unique()
    
    team_map = {}
    # Lookup fra din centrale TEAMS fil
    mapping_lookup = {str(info.get('opta_uuid', '')).lower().replace('t', ''): name for name, info in TEAMS.items()}
    
    for u_raw in ids_i_ligaen:
        if pd.isna(u_raw): continue
        u_clean = str(u_raw).lower().strip().replace('t', '')
        matched_name = None
        
        # 1. Tjek TEAMS mapping
        for m_id, name in mapping_lookup.items():
            if m_id and (m_id in u_clean or u_clean in m_id):
                matched_name = name
                break
        
        # 2. Hvis ikke i TEAMS, find navnet i df_matches
        if not matched_name:
            match_row = df_matches[df_matches['CONTESTANTHOME_OPTAUUID'] == u_raw]
            if not match_row.empty:
                matched_name = match_row['CONTESTANTHOME_NAME'].iloc[0]
            else:
                match_away = df_matches[df_matches['CONTESTANTAWAY_OPTAUUID'] == u_raw]
                if not match_away.empty:
                    matched_name = match_away['CONTESTANTAWAY_NAME'].iloc[0]

        if not matched_name:
            matched_name = f"Ukendt ({u_clean[:5]})"
            
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

    # 1. Byg mappet (Vi fjerner COMP-filteret for at sikre, at vi ser alle hold i pakken)
    team_map = build_team_map(df_matches)  # Kun ét argument her!
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
        # --- TAB 1 (index 0): MED BOLD ---
    # --- TAB 1 (index 0): MED BOLD ---
    # --- TAB 1 (index 0): MED BOLD ---
    with tabs[0]:
        fokus = st.radio("Fokus:", ["Opbygning", "Gennembrud"], horizontal=True)
        c1, c2 = st.columns(2)
        
        # Sortering for at sikre shift() virker til progressive pile
        df_h_ev = df_h_ev.sort_values(['EVENT_TIMEMIN', 'EVENT_TIMESEC'])

        if fokus == "Opbygning":
            with c1:
                st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>MÅLSPARK</p>", unsafe_allow_html=True)
                df_f = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['EVENT_X'] < 15)]
                
                fig, ax = pitch.draw(figsize=(4, 5))
                if not df_f.empty:
                    # zorder=1 sikrer at den ligger under banens streger (hvis man vil have dem synlige)
                    sns.kdeplot(x=df_f['EVENT_Y'], y=df_f['EVENT_X'], fill=True, cmap='Reds', alpha=0.6, 
                                ax=ax, bw_adjust=0.8, clip=((0, 100), (0, 100)), zorder=0)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

            with c2:
                st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>OPBYGNING</p>", unsafe_allow_html=True)
                df_f = df_h_ev[(df_h_ev['EVENT_TYPEID'] == 1) & (df_h_ev['EVENT_X'].between(15, 50))]
                fig, ax = pitch.draw(figsize=(4, 5))
                if not df_f.empty:
                    sns.kdeplot(x=df_f['EVENT_Y'], y=df_f['EVENT_X'], fill=True, cmap='Reds', alpha=0.6, 
                                ax=ax, bw_adjust=0.8, clip=((0, 100), (0, 100)), zorder=0)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)
        else:
            with c1:
                st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>GENNEMBRUD</p>", unsafe_allow_html=True)
                df_f = df_h_ev[df_h_ev['EVENT_X'] > 66]
                
                # Her tegner vi banen FØRST
                fig, ax = pitch.draw(figsize=(4, 5))
                
                if not df_f.empty:
                    # clip fjerner de hvide områder udenfor banen
                    sns.kdeplot(x=df_f['EVENT_Y'], y=df_f['EVENT_X'], fill=True, cmap='Oranges', 
                                alpha=0.6, ax=ax, bw_adjust=0.8, clip=((0, 100), (0, 100)), zorder=0)
                
                # Sæt banens rammer hårdt så de ikke skifter
                ax.set_xlim(0, 100)
                ax.set_ylim(0, 100)
                draw_logo_on_ax(ax, t_logo)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

            with c2:
                st.write("<p style='text-align:center; font-size:12px; font-weight:bold;'>PROGRESSIVE</p>", unsafe_allow_html=True)
                
                # Beregn næste position til pile
                df_prog_calc = df_h_ev.copy()
                df_prog_calc['NEXT_X'] = df_prog_calc['EVENT_X'].shift(-1)
                df_prog_calc['NEXT_Y'] = df_prog_calc['EVENT_Y'].shift(-1)
                
                df_prog = df_prog_calc[
                    (df_prog_calc['EVENT_TYPEID'] == 1) & 
                    (df_prog_calc['NEXT_X'] > (df_prog_calc['EVENT_X'] + 15))
                ]
                
                fig, ax = pitch.draw(figsize=(4, 5))
                # Vi tvinger aksen til at blive på banen
                ax.set_xlim(0, 100)
                ax.set_ylim(0, 100)
                
                if not df_prog.empty:
                    pitch.arrows(df_prog.EVENT_X, df_prog.EVENT_Y, 
                                 df_prog.NEXT_X, df_prog.NEXT_Y, 
                                 width=1.5, color=t_color, ax=ax, alpha=0.6, zorder=2)
                
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
