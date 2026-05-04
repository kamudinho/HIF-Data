import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from mplsoccer import Pitch
from data.data_load import _get_snowflake_conn
from data.utils.team_mapping import TEAMS
import requests
from PIL import Image
from io import BytesIO

# --- IMPORT FRA MAPPING ---
from data.utils.mapping import (
    OPTA_EVENT_TYPES, 
    OPTA_QUALIFIERS,
    get_action_label
)

# --- KONFIGURATION ---
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_IDS = "('dyjr458hcmrcy87fsabfsy87o', 'e5p78j2r7v8h3u9s5k0l2m4n6', 'f6q89k3s8w9i4v0t6l1m3n5o7', '335', '328', '329', '43319', '331')"
SEASONNAME = "2025/2026"

# --- HJÆLPEFUNKTIONER ---
@st.cache_data(ttl=3600)
def get_logo_img(opta_uuid):
    if not opta_uuid: return None
    uuid_clean = str(opta_uuid).lower().replace('t', '')
    url = next((info['logo'] for name, info in TEAMS.items() if str(info.get('opta_uuid', '')).lower().replace('t','') == uuid_clean), None)
    if not url: return None
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except: return None

def draw_player_info_box(ax, logo, player_name, season, view_name):
    ax.add_patch(plt.Rectangle((1, 85), 38, 14, color='#003366', alpha=0.9, zorder=10))
    ax.text(12, 95, player_name.upper(), color='white', fontsize=10, fontweight='bold', zorder=11)
    ax.text(12, 91, f"{season} | {view_name}", color='white', fontsize=8, alpha=0.8, zorder=11)
    if logo:
        logo_arr = np.array(logo.convert("RGBA"))
        newax = ax.inset_axes([0.02, 0.87, 0.08, 0.1], zorder=12)
        newax.imshow(logo_arr)
        newax.axis('off')

def create_relative_donut(player_val, max_val, label, color="#003366"):
    base_max = max(max_val, player_val, 1)
    remainder = max(0, base_max - player_val)
    fig = go.Figure(go.Pie(
        values=[player_val, remainder],
        hole=0.7,
        marker_colors=[color, "#EEEEEE"],
        textinfo='none',
        hoverinfo='none'
    ))
    pct = int((player_val / base_max) * 100) if base_max > 0 else 0
    fig.update_layout(
        showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=130, width=130,
        annotations=[dict(text=f"{player_val}<br><span style='font-size:10px;'>{pct}% af maks</span>", 
                     x=0.5, y=0.5, font_size=16, showarrow=False, font_family="Arial Black")]
    )
    return fig

def get_physical_data(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_cond = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])
    sql = f"""
        SELECT p.MATCH_DATE, MAX(p.MINUTES) as MINUTES, SUM(p.DISTANCE) as DISTANCE,
               SUM(p."HIGH SPEED RUNNING") as HSR, SUM(p.SPRINTING) as SPRINTING,
               MAX(p.TOP_SPEED) as TOP_SPEED
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        WHERE (({name_cond}) OR ("optaId" LIKE '%{clean_id}%'))
          AND p.MATCH_DATE >= '2025-07-01'
        GROUP BY p.MATCH_DATE, p.PLAYER_NAME ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side():
    st.markdown("<style>[data-testid='stMetricValue'] { font-size: 18px !important; text-align: center; font-weight: bold; }</style>", unsafe_allow_html=True)
    conn = _get_snowflake_conn()
    if not conn: return

    # --- TOP MENU ---
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    team_map = {mapping_lookup[str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')]: r['CONTESTANTHOME_OPTAUUID'] 
                for _, r in df_teams_raw.iterrows() if str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','') in mapping_lookup}

    col_logo, col_space, col_h_hold, col_h_spiller = st.columns([1, 2.5, 1.2, 1.2])

    with col_h_hold:
        valgt_hold = st.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
        valgt_uuid_hold = team_map[valgt_hold]
    
    hold_logo = get_logo_img(valgt_uuid_hold)
    with col_logo:
        if hold_logo: st.image(hold_logo, width=80)

    # --- HENT DATA ---
    sql_events = f"""
        SELECT e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
               e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME, 
               LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
        FROM {DB}.OPTA_EVENTS e
        JOIN {DB}.OPTA_PLAYERS p ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
        WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' AND e.EVENT_TIMESTAMP >= '2025-07-01'
        GROUP BY 1, 2, 3, 4, 5, 6
    """
    df_all = conn.query(sql_events)
    
    if df_all is None or df_all.empty:
        st.warning("Ingen data fundet.")
        return

    df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)
    
    # RETTELSE: Fjern NoneType før sortering for at undgå '<' fejl
    spiller_liste = sorted([s for s in df_all['VISNINGSNAVN'].unique() if s is not None])
    
    with col_h_spiller:
        valgt_spiller = st.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
        spiller_info = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].iloc[0]
        valgt_player_uuid = spiller_info['PLAYER_OPTAUUID']
        df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    # --- TABS ---
    t_profile, t_pitch, t_phys, t_stats, t_compare = st.tabs(["Profil", "Aktioner", "Fysisk", "Statistik", "Sammenligning"])

    with t_profile:
        col_card, col_main = st.columns([1, 3.5])
        with col_card:
            maal = len(df_spiller[df_spiller['EVENT_TYPEID'] == 16])
            assists = len(df_spiller[df_spiller['QUALIFIERS'].fillna('').str.contains('154')])
            st.markdown(f"""<div style='background:#003366;color:white;padding:15px;border-radius:10px;'>
                <h4>{valgt_spiller}</h4><hr>Mål: {maal}<br>Assists: {assists}</div>""", unsafe_allow_html=True)
        
        with col_main:
            # Beregn truppens maks-værdier for relativ visning
            truppen = df_all.groupby('VISNINGSNAVN').agg(
                p=('EVENT_TYPEID', lambda x: (x == 1).sum()),
                m=('EVENT_TYPEID', lambda x: (x == 16).sum()),
                s=('EVENT_TYPEID', lambda x: x.isin([13, 14, 15, 16]).sum()),
                a=('EVENT_TYPEID', 'count')
            )
            s_val = truppen.loc[valgt_spiller]
            c1, c2, c3, c4 = st.columns(4)
            c1.plotly_chart(create_relative_donut(s_val['p'], truppen['p'].max(), "Pasninger"), config={'displayModeBar': False})
            c2.plotly_chart(create_relative_donut(s_val['m'], truppen['m'].max(), "Mål", "#11caa0"), config={'displayModeBar': False})
            c3.plotly_chart(create_relative_donut(s_val['s'], truppen['s'].max(), "Skud"), config={'displayModeBar': False})
            c4.plotly_chart(create_relative_donut(s_val['a'], truppen['a'].max(), "Total", "#FFD700"), config={'displayModeBar': False})

    with t_pitch:
        col_p1, col_p2 = st.columns([1, 4])
        with col_p1:
            labels = sorted([l for l in df_spiller['Action_Label'].unique() if l])
            valgt_label = st.multiselect("Filtrer aktioner", labels, default=[l for l in ["Shot", "Goal"] if l in labels])
        with col_p2:
            pitch = Pitch(pitch_type='opta', pitch_color='#f8f8f8', line_color='#888888')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, SEASONNAME, "Positionskort")
            plot_df = df_spiller[df_spiller['Action_Label'].isin(valgt_label)]
            pitch.scatter(plot_df.EVENT_X, plot_df.EVENT_Y, ax=ax, alpha=0.7, s=100, edgecolors='white', color='#003366')
            st.pyplot(fig)

    with t_phys:
        if df_phys is not None and not df_phys.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Gns. Distance", f"{round(df_phys['DISTANCE'].mean()/1000, 2)} km")
            m2.metric("Gns. HSR", f"{int(df_phys['HSR'].mean())} m")
            m3.metric("Gns. Sprints", f"{int(df_phys['SPRINTING'].mean())} m")
            m4.metric("Top Speed", f"{round(df_phys['TOP_SPEED'].max(), 1)} km/h")
            fig_dist = go.Figure(go.Bar(x=df_phys['MATCH_DATE'], y=df_phys['DISTANCE'], marker_color='#003366'))
            fig_dist.update_layout(title="Distance pr. kamp", height=300, margin=dict(t=30, b=0))
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info("Ingen fysiske data tilgængelige.")

    with t_stats:
        st.subheader("Aktionsoversigt")
        stats_df = df_spiller['Action_Label'].value_counts().reset_index()
        stats_df.columns = ['Aktion', 'Antal']
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

    with t_compare:
        st.subheader("Sammenlign med holdkammerat")
        modstander = st.selectbox("Vælg spiller at sammenligne med", [s for s in spiller_liste if s != valgt_spiller])
        df_comp = df_all[df_all['VISNINGSNAVN'] == modstander]
        
        c_left, c_right = st.columns(2)
        c_left.write(f"**{valgt_spiller}**")
        c_left.write(f"Total aktioner: {len(df_spiller)}")
        c_right.write(f"**{modstander}**")
        c_right.write(f"Total aktioner: {len(df_comp)}")

if __name__ == "__main__":
    vis_side()
