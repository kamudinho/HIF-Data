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
def draw_remote_pitch(df_row, title, color, logo):
    pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333', line_zorder=2)
    fig, ax = pitch.draw(figsize=(6, 8))
    ax.text(50, 103, title, color='black', va='center', ha='center', fontsize=14, fontweight='bold')
    
    if not df_row.empty:
        formation = df_row.get('SHAPE_FORMATION', 'N/A')
        roles_raw = df_row.get('SHAPE_ROLE', [])
        try:
            roles = json.loads(roles_raw) if isinstance(roles_raw, str) else roles_raw
            if isinstance(roles, list):
                for r in roles:
                    x, y = float(r.get('averageRolePositionX', 50)), float(r.get('averageRolePositionY', 50))
                    num = r.get('shirtNumber', '')
                    ax.scatter(y, x, s=700, color=color, edgecolors='black', linewidth=1.5, zorder=3)
                    ax.text(y, x, str(num), color='white', ha='center', va='center', fontsize=11, fontweight='bold', zorder=4)
                ax.text(50, 2, f"Formation: {formation}", color='gray', ha='center', fontsize=10, fontweight='bold')
        except: pass
            
    draw_logo_on_ax(ax, logo)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

# --- 3. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    st.markdown("<style>.block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)

    if not analysis_package:
        st.error("Ingen data fundet i analysis_package.")
        return

    # 1. HENT DATA
    df_matches = analysis_package.get("matches", pd.DataFrame())
    df_remote_raw = analysis_package.get("remote_shapes", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())

    # 2. PARSING (Vi tvinger data frem)
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

    with tabs[0]:
        # --- DEBUG SEKTION (Altid synlig mens vi fejlsøger) ---
        st.info("🛠 **Debug Information**")
        col_db1, col_db2 = st.columns(2)
        with col_db1:
            st.write(f"**Valgt hold UUID:** `{hold_uuid}`")
            st.write(f"**Søger efter (15 tegn):** `{hold_uuid[:15]}`")
        with col_db2:
            unique_uuids = df_remote['CONTESTANT_OPTAUUID'].unique().tolist() if not df_remote.empty else []
            st.write(f"**UUIDs i Remote Data:** `{unique_uuids[:3]}`")
            st.write(f"**Antal rækker i Remote:** `{len(df_remote)}`")
        
        st.divider()

        if not df_remote.empty and hold_uuid:
            # Matcher på de første 15 tegn
            df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'].str.contains(hold_uuid[:15], na=False)]
            
            if not df_h.empty:
                t_options = sorted(df_h['SHAPE_TIMEELAPSEDSTART'].unique().tolist())
                t_step = st.select_slider("Vælg spilfase (sekunder):", options=t_options)
                
                df_s = df_h[df_h['SHAPE_TIMEELAPSEDSTART'] == t_step]
                
                c1, c2 = st.columns(2)
                with c1:
                    row_in = df_s[df_s['POSSESSION_TYPE'].str.contains('inPossession', case=False)]
                    draw_remote_pitch(row_in.iloc[0] if not row_in.empty else pd.Series(), "OFFENSIV", t_color, t_logo)
                with c2:
                    row_out = df_s[df_s['POSSESSION_TYPE'].str.contains('outOfPossession', case=False)]
                    draw_remote_pitch(row_out.iloc[0] if not row_out.empty else pd.Series(), "DEFENSIV", "#333333", t_logo)
            else:
                st.error(f"Ingen match fundet mellem {valgt_hold}'s UUID og dataen i remote_shapes.")
                if st.checkbox("Vis rå data fra remote_shapes"):
                    st.dataframe(df_remote)
        else:
            st.warning("Data mangler: Enten er remote_shapes tom eller UUID kunne ikke findes.")

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
