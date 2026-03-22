import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import requests
from io import BytesIO
from PIL import Image
import json
from data.utils.team_mapping import TEAMS, TEAM_COLORS, COMPETITIONS, COMPETITION_NAME

# --- 1. HJÆLPEFUNKTIONER (LOGO & FARVER) ---
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
    # Opta koordinater: X er længden (0-100), Y er bredden (0-100)
    res[['averageRolePositionX', 'averageRolePositionY']] = res[['averageRolePositionX', 'averageRolePositionY']].apply(pd.to_numeric)
    
    # KRITISK KOORDINAT-FIX FOR OPTA -> VERTICALPITCH
    # For at undgå at spillerne maser i bunden, skal vi vende X-aksen
    res['x_plot'] = res['averageRolePositionX'] 
    res['y_plot'] = res['averageRolePositionY'] # Y er bredden, skal plottes direkte
    
    return res.groupby('shirtNumber').agg({'x_plot':'mean', 'y_plot':'mean'}).reset_index()

# --- 2. MASTER MATCHER (TURNERINGS-FILTER) ---
def build_team_map(df_remote, df_matches):
    # Hent det korrekte UUID fra din mapping-fil (f.eks. 1. Division: "6ifaeunfdele")
    target_comp_uuid = COMPETITIONS.get(COMPETITION_NAME, {}).get("COMPETITION_OPTAUUID")
    
    # Filtrer matches så vi kun har den valgte turnering
    if target_comp_uuid and 'COMPETITION_OPTAUUID' in df_matches.columns:
        df_matches = df_matches[df_matches['COMPETITION_OPTAUUID'] == target_comp_uuid]

    raw_uuids = df_remote['CONTESTANT_OPTAUUID'].unique().tolist()
    team_map = {}
    mapping_lookup = {str(info.get('opta_uuid', '')).lower()[:8]: name for name, info in TEAMS.items()}
    
    db_teams = pd.DataFrame()
    if not df_matches.empty:
        home = df_matches[['CONTESTANTHOME_OPTAUUID', 'CONTESTANTHOME_NAME']].rename(columns={'CONTESTANTHOME_OPTAUUID': 'id', 'CONTESTANTHOME_NAME': 'name'})
        away = df_matches[['CONTESTANTAWAY_OPTAUUID', 'CONTESTANTAWAY_NAME']].rename(columns={'CONTESTANTAWAY_OPTAUUID': 'id', 'CONTESTANTAWAY_NAME': 'name'})
        db_teams = pd.concat([home, away]).drop_duplicates()

    for u_raw in raw_uuids:
        u_clean = str(u_raw).lower().strip()
        
        # Tjek om dette hold overhovedet findes i vores filtrerede 1. Division matches
        if not db_teams.empty and u_clean not in db_teams['id'].str.lower().tolist():
            continue # Spring over hvis holdet ikke hører til 1. Division
            
        matched_name = None
        for m_id, name in mapping_lookup.items():
            if m_id and (m_id in u_clean or u_clean.startswith(m_id)):
                matched_name = name
                break
        if not matched_name and not db_teams.empty:
            match_row = db_teams[db_teams['id'].str.lower() == u_clean]
            if not match_row.empty: matched_name = match_row['name'].iloc[0]
        
        if matched_name:
            team_map[matched_name] = u_raw
            
    return team_map

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    if not analysis_package:
        st.error("Ingen data fundet.")
        return

    df_remote = analysis_package.get("remote_shapes", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_matches = analysis_package.get("matches", pd.DataFrame())

    if df_remote.empty:
        st.warning(f"Ingen positionsdata fundet for {COMPETITION_NAME}.")
        return

    # Byg hold-oversigten (nu filtreret på turneringens UUID)
    team_map = build_team_map(df_remote, df_matches)
    
    if not team_map:
        st.warning(f"Ingen hold fundet for {COMPETITION_NAME} i denne pakke.")
        return

    # UI - Vælg hold (Kompakt format uden label)
    valgt_hold = st.selectbox("Vælg hold:", sorted(list(team_map.keys())), label_visibility="collapsed")
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)
    
    # ID reference til hændelser (Top 5 fanen)
    event_uuid_ref = str(valgt_uuid_data).lower()[:8]

    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # Pitch definition (Fælles indstillinger for alle baner)
    # Vi bruger 'opta' koordinater (0-100)
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', linewidth=2)

    # --- TAB 0: STRUKTUR (LAYOUT-RETTET SÅ ALT KAN SES) ---
    with tabs[0]:
        df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'] == valgt_uuid_data]
        formation = df_h['SHAPE_FORMATION'].iloc[-1] if 'SHAPE_FORMATION' in df_h.columns else "N/A"
        
        # --- NY LOGIK FOR AT UNDGÅ SCROLLING ---
        # I stedet for st.columns(2), viser vi nu kun én bane ad gangen.
        # En lille radioknap lader brugeren skifte fase.
        c1, c2 = st.columns([2, 1])
        with c1:
            st.caption(f"**{valgt_hold}** | Formation: {formation}")
        with c2:
            fase = st.radio("Vis fase:", ["Offensiv", "Defensiv"], horizontal=True, label_visibility="collapsed")
        
        # Sæt data og titel baseret på radioknappen
        if fase == "Offensiv":
            data = get_avg(df_h, 'inPossession')
            dot_color = t_color
            titel = "STRUKTUR - MED BOLD"
        else:
            data = get_avg(df_h, 'outOfPossession')
            dot_color = "#333333"
            titel = "STRUKTUR - MOD BOLD"
        
        # Nu tegner vi banen i fuld bredde (én bane), så den kan folde sig ud uden scroll
        if not data.empty:
            st.write(f"<p style='text-align:center; font-size:14px;'>{titel}</p>", unsafe_allow_html=True)
            # Figsize (6, 8) giver en stor, tydelig bane uden scrolling når use_container_width=True
            fig, ax = pitch.draw(figsize=(6, 8))
            
            # Plot koordinater (Y er bredden, X er længden)
            ax.scatter(data['y_plot'], data['x_plot'], s=350, color=dot_color, edgecolors='black', linewidth=1.5, zorder=3)
            for _, row in data.iterrows():
                ax.text(row['y_plot'], row['x_plot'], str(int(row['shirtNumber'])), 
                        color='white', ha='center', va='center', fontsize=8, fontweight='bold', zorder=4)
            
            draw_logo_on_ax(ax, t_logo)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.warning(f"Ingen positionsdata fundet for {fase} fase.")

    # De andre tabs forbliver side-om-side, da de er halve baner eller fylder minimalt...
    with tabs[1]: # MED BOLD (Half pitches)
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if not df_h_ev.empty:
                half_pitch = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333', linewidth=1.5)
                c1, c2 = st.columns(2)
                for col, title, x_lim in zip([c1, c2], ["OPBYGNING", "AFSLUTNING"], [(0,50), (50,100)]):
                    with col:
                        st.write(f"<p style='text-align:center; font-size:12px;'>{title}</p>", unsafe_allow_html=True)
                        fig, ax = half_pitch.draw(figsize=(4, 4))
                        df_z = df_h_ev[(df_h_ev['EVENT_TYPEID']==1) & (df_h_ev['LOCATIONX'].between(x_lim[0], x_lim[1]))]
                        if not df_z.empty:
                            sns.kdeplot(x=df_z['LOCATIONY'], y=df_z['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax, bw_adjust=0.8)
                        draw_logo_on_ax(ax, t_logo); st.pyplot(fig, use_container_width=True); plt.close(fig)

    with tabs[3]: # TOP 5
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            c1, c2, c3 = st.columns(3)
            metrics = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
            for col, (ids, label) in zip([c1, c2, c3], metrics):
                with col:
                    st.write(f"**{label}**")
                    stats = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(ids)]['PLAYER_NAME'].value_counts().head(5)
                    for n, v in stats.items(): st.write(f"{v} {n}")
