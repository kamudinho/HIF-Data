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

# --- 2. HOVEDFUNKTION ---
def vis_side(analysis_package=None):
    st.markdown("<style>.block-container { padding-top: 1rem; }</style>", unsafe_allow_html=True)
    
    if not analysis_package:
        st.error("Ingen data fundet.")
        return

    df_remote = analysis_package.get("remote_shapes", pd.DataFrame())
    df_events = analysis_package.get("opta", {}).get("events", pd.DataFrame())
    df_matches = analysis_package.get("matches", pd.DataFrame())

    if df_remote.empty:
        st.warning("Ingen positionsdata (remote_shapes) fundet.")
        return

    # --- KONTANT DEBUG (VISER OS HVAD DER ER I DATABASEN) ---
    raw_uuids = df_remote['CONTESTANT_OPTAUUID'].unique().tolist()
    st.info(f"DEBUG - Fundet i database: {raw_uuids}")

    # --- DEN NYE AGGRESSIVE MATCHER ---
    team_map = {} 
    h_name_db = df_matches['CONTESTANTHOME_NAME'].iloc[0] if not df_matches.empty else "Hjemmehold"
    a_name_db = df_matches['CONTESTANTAWAY_NAME'].iloc[0] if not df_matches.empty else "Udehold"

    for i, u_raw in enumerate(raw_uuids):
        u_clean = str(u_raw).strip().lower()
        matched_name = None
        
        # Tjek din team_mapping.py (TEAMS)
        for t_name, t_info in TEAMS.items():
            # Vi tjekker 'opta_uuid' feltet fra din fil
            m_uuid = str(t_info.get('opta_uuid', '')).strip().lower()
            if m_uuid and (m_uuid[:8] in u_clean or u_clean[:8] in m_uuid):
                matched_name = t_name
                break
        
        # Hvis intet match, brug navnene fra kampen
        if not matched_name:
            matched_name = h_name_db if i == 0 else a_name_db
            
        team_map[matched_name] = u_raw

    # UI
    valgt_hold = st.selectbox("Vælg hold:", sorted(list(team_map.keys())))
    valgt_uuid_data = team_map[valgt_hold]
    t_color, t_logo = get_team_style(valgt_hold)
    
    # ID til hændelser
    event_uuid_ref = str(valgt_uuid_data).lower()[:8]

    tabs = st.tabs(["STRUKTUR", "MED BOLD", "MOD BOLD", "TOP 5"])

    # --- TAB 0: STRUKTUR ---
    with tabs[0]:
        df_h = df_remote[df_remote['CONTESTANT_OPTAUUID'] == valgt_uuid_data]
        formation = df_h['SHAPE_FORMATION'].iloc[-1] if 'SHAPE_FORMATION' in df_h.columns else "N/A"
        st.subheader(f"{valgt_hold} - Formation: {formation}")
        
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
            res[['averageRolePositionX', 'averageRolePositionY']] = res[['averageRolePositionX', 'averageRolePositionY']].apply(pd.to_numeric)
            return res.groupby('shirtNumber').agg({'averageRolePositionX':'mean', 'averageRolePositionY':'mean'}).reset_index()

        avg_in = get_avg(df_h, 'inPossession')
        avg_out = get_avg(df_h, 'outOfPossession')
        
        c1, c2 = st.columns(2)
        with c1:
            st.caption("🔴 **OFFENSIV**")
            pitch = VerticalPitch(pitch_type='opta', pitch_color='#ffffff', line_color='#333333')
            fig, ax = pitch.draw(figsize=(4, 5))
            if not avg_in.empty:
                for _, row in avg_in.iterrows():
                    ax.scatter(row['averageRolePositionY'], row['averageRolePositionX'], s=250, color=t_color, edgecolors='black', zorder=3)
                    ax.text(row['averageRolePositionY'], row['averageRolePositionX'], str(int(row['shirtNumber'])), color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
            draw_logo_on_ax(ax, t_logo); st.pyplot(fig); plt.close(fig)
        with c2:
            st.caption("⚪ **DEFENSIV**")
            fig, ax = pitch.draw(figsize=(4, 5))
            if not avg_out.empty:
                for _, row in avg_out.iterrows():
                    ax.scatter(row['averageRolePositionY'], row['averageRolePositionX'], s=250, color="#333333", edgecolors='black', zorder=3)
                    ax.text(row['averageRolePositionY'], row['averageRolePositionX'], str(int(row['shirtNumber'])), color='white', ha='center', va='center', fontsize=7, fontweight='bold', zorder=4)
            draw_logo_on_ax(ax, t_logo); st.pyplot(fig); plt.close(fig)

    # --- TABS FOR HEATMAPS & TOP 5 ---
    with tabs[1]: # MED BOLD
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            if not df_h_ev.empty:
                pitch_h = VerticalPitch(pitch_type='opta', half=True, pitch_color='#ffffff', line_color='#333333')
                cols = st.columns(2)
                for col, title, x_lim in zip(cols, ["OPBYGNING", "AFSLUTNING"], [(0,50), (50,100)]):
                    with col:
                        st.write(f"**{title}**")
                        fig, ax = pitch_h.draw(figsize=(4,5))
                        ax.set_ylim(x_lim[0], x_lim[1])
                        df_z = df_h_ev[(df_h_ev['EVENT_TYPEID']==1) & (df_h_ev['LOCATIONX'].between(x_lim[0], x_lim[1]))]
                        if not df_z.empty:
                            sns.kdeplot(x=df_z['LOCATIONY'], y=df_z['LOCATIONX'], fill=True, cmap='Reds', alpha=0.5, ax=ax, bw_adjust=0.8)
                        draw_logo_on_ax(ax, t_logo); st.pyplot(fig); plt.close(fig)
            else: st.info("Ingen hændelses-data fundet for dette hold.")

    with tabs[3]: # TOP 5
        if not df_events.empty:
            df_h_ev = df_events[df_events['EVENT_CONTESTANT_OPTAUUID'].str.lower().str.contains(event_uuid_ref, na=False)]
            c1, c2, c3 = st.columns(3)
            metrics = [([1], 'Afleveringer'), ([4,5], 'Dueller'), ([8,49], 'Erobringer')]
            for col, (ids, label) in zip([c1, c2, c3], metrics):
                with col:
                    st.subheader(label)
                    stats = df_h_ev[df_h_ev['EVENT_TYPEID'].isin(ids)]['PLAYER_NAME'].value_counts().head(5)
                    for n, v in stats.items(): st.write(f"**{v}** {n}")
