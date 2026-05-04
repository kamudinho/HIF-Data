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
CURRENT_SEASON = "2025/2026"

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

def draw_player_info_box(ax, team_logo, player_name, season_str, category_str):
    if team_logo:
        ax_l = ax.inset_axes([0.02, 0.88, 0.07, 0.07], transform=ax.transAxes)
        ax_l.imshow(team_logo)
        ax_l.axis('off')
    ax.text(0.10, 0.92, str(player_name).upper(), transform=ax.transAxes, 
            fontsize=10, fontweight='bold', color='black', va='center')
    ax.text(0.10, 0.89, f"{season_str} | {category_str}", transform=ax.transAxes, 
            fontsize=8, color='#666666', va='center')

def create_donut_chart(value, label, color="#003366"):
    """Hjælpefunktion til at lave cirkel-statistikker (donuts)"""
    fig = go.Figure(go.Pie(
        values=[value, max(1, 100-value) if "%" in str(label) else 0],
        hole=0.7,
        marker_colors=[color, "#EEEEEE"],
        textinfo='none',
        hoverinfo='none'
    ))
    fig.update_layout(
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        height=150,
        width=150,
        annotations=[dict(text=str(value), x=0.5, y=0.5, font_size=20, showarrow=False, font_family="Arial Black")]
    )
    return fig

def get_physical_data(player_name, player_opta_uuid, valgt_hold_navn, db_conn):
    target_ssiid = TEAMS.get(valgt_hold_navn, {}).get('ssid')
    if not target_ssiid:
        target_ssiid = '56fa29c7-3a48-4186-9d14-dbf45fbc78d9'

    clean_id = str(player_opta_uuid).lower().replace('p', '').strip()
    navne_dele = [n.strip() for n in player_name.split(' ') if len(n.strip()) > 2]
    name_conditions = " OR ".join([f"PLAYER_NAME ILIKE '%{n}%'" for n in navne_dele])

    sql = f"""
        SELECT 
            p.MATCH_DATE,
            ANY_VALUE(p.MATCH_TEAMS) as MATCH_TEAMS,
            MAX(p.MINUTES) as MINUTES,
            SUM(p.DISTANCE) as DISTANCE,
            SUM(p."HIGH SPEED RUNNING") as HSR,
            SUM(p.SPRINTING) as SPRINTING,
            MAX(p.TOP_SPEED) as TOP_SPEED,
            SUM(p.NO_OF_HIGH_INTENSITY_RUNS) as HI_RUNS
        FROM {DB}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS p
        WHERE (({name_conditions}) OR ("optaId" LIKE '%{clean_id}%'))
          AND p.MATCH_DATE BETWEEN '2025-07-01' AND '2026-06-30'
          AND p.MATCH_SSIID IN (
              SELECT MATCH_SSIID 
              FROM {DB}.SECONDSPECTRUM_GAME_METADATA
              WHERE HOME_SSIID = '{target_ssiid}' 
                 OR AWAY_SSIID = '{target_ssiid}'
          )
        GROUP BY p.MATCH_DATE, p.PLAYER_NAME
        ORDER BY p.MATCH_DATE DESC
    """
    return db_conn.query(sql)

def vis_side():
    st.set_page_config(layout="wide")
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        [data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; }
        .player-header { font-size: 24px; font-weight: bold; color: #003366; margin-bottom: 5px; }
        .stat-box { background-color: #f8f9fa; border-radius: 10px; padding: 15px; text-align: center; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
        .profile-card { background-color: #003366; color: white; padding: 20px; border-radius: 15px; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # 1. HOLDVALG & TOP-MENU
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}

    team_map = {}
    if df_teams_raw is not None:
        for _, r in df_teams_raw.iterrows():
            uuid_clean = str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')
            if uuid_clean in mapping_lookup:
                team_map[mapping_lookup[uuid_clean]] = r['CONTESTANTHOME_OPTAUUID']

    # Layout til valg af hold og spiller øverst
    col_logo, col_h_hold, col_h_spiller, col_spacer = st.columns([1, 2, 2, 5])
    valgt_hold = col_h_hold.selectbox("Vælg Hold", sorted(list(team_map.keys())))
    valgt_uuid_hold = team_map[valgt_hold]
    hold_logo = get_logo_img(valgt_uuid_hold)
    if hold_logo: col_logo.image(hold_logo, width=80)

    # 2. HENT DATA
    with st.spinner("Henter data..."):
        sql = f"""
            SELECT 
                e.EVENT_X, e.EVENT_Y, e.EVENT_TYPEID, 
                TRIM(p.FIRST_NAME) || ' ' || TRIM(p.LAST_NAME) as VISNINGSNAVN, 
                e.PLAYER_OPTAUUID, e.EVENT_OUTCOME as OUTCOME,
                TO_CHAR(e.EVENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as EVENT_TIMESTAMP_STR,
                LISTAGG(q.QUALIFIER_QID, ',') WITHIN GROUP (ORDER BY q.QUALIFIER_QID) as QUALIFIERS
            FROM {DB}.OPTA_EVENTS e
            JOIN (SELECT DISTINCT PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME FROM {DB}.OPTA_PLAYERS WHERE FIRST_NAME IS NOT NULL) p 
                ON e.PLAYER_OPTAUUID = p.PLAYER_OPTAUUID
            LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID
            WHERE e.EVENT_CONTESTANT_OPTAUUID = '{valgt_uuid_hold}' 
            AND e.EVENT_TIMESTAMP >= '2025-07-01'
            GROUP BY 1, 2, 3, 4, 5, 6, 7
        """
        df_all = conn.query(sql)
        if df_all is None or df_all.empty:
            st.warning("Ingen hændelsesdata fundet.")
            return
        
        df_all['qual_list'] = df_all['QUALIFIERS'].fillna('').str.split(',')
        df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)

    spiller_liste = sorted(df_all['VISNINGSNAVN'].unique())
    valgt_spiller = col_h_spiller.selectbox("Vælg Spiller", spiller_liste)
    valgt_player_uuid = df_all[df_all['VISNINGSNAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
    df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    # TABS
    t_profile, t_pitch, t_phys, t_stats = st.tabs(["Spillerprofil", "Spilleraktioner", "Fysisk data", "Statistik"])

    # --- TAB 1: SPILLERPROFIL (NY) ---
    with t_profile:
        col_card, col_main = st.columns([1, 3])
        
        with col_card:
            # Spiller-info boks (Blå boks til venstre)
            st.markdown(f"""
                <div class="profile-card">
                    <h2 style='margin:0;'>{valgt_spiller}</h2>
                    <p style='margin:0; opacity:0.8;'>Position: Midtbane</p>
                    <hr style='border-color: rgba(255,255,255,0.2);'>
                    <table style='width:100%; font-size:14px;'>
                        <tr><td>Kampe:</td><td style='text-align:right;'><b>16</b></td></tr>
                        <tr><td>Minutter:</td><td style='text-align:right;'><b>1423</b></td></tr>
                        <tr><td>Mål:</td><td style='text-align:right;'><b>3</b></td></tr>
                        <tr><td>Assists:</td><td style='text-align:right;'><b>4</b></td></tr>
                    </table>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            # Volumen-bars (som på billedet)
            st.write("Volumen i forhold til liga")
            metrics = {
                "Afleveringer": 29.2,
                "Dueller": 25.7,
                "Boldtab": 11.6,
                "Skud": 1.7,
                "xG": 0.3,
                "Pasnings %": 77.4
            }
            for m, val in metrics.items():
                st.write(f"<div style='font-size:12px; margin-bottom:-10px;'>{m} <span style='float:right;'>{val}</span></div>", unsafe_allow_html=True)
                st.progress(min(val/50 if "Pasning" not in m else val/100, 1.0))

        with col_main:
            st.markdown("<h3 style='text-align:center; color:#003366;'>Spillerstatistik</h3>", unsafe_allow_html=True)
            
            # Beregn værdier fra data (Her bruger vi dummy-tal eller simpel optælling)
            pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
            pas_total = len(pas_df)
            pas_acc = int((pas_df['OUTCOME'].sum() / pas_total * 100)) if pas_total > 0 else 0
            
            # Donut grid 4x3
            r1 = st.columns(4)
            with r1[0]: st.write("Afleveringer"); st.plotly_chart(create_donut_chart(pas_total, "Total"), config={'displayModeBar': False})
            with r1[1]: st.write("Pasning %"); st.plotly_chart(create_donut_chart(pas_acc, "Acc %", color="#11caa0"), config={'displayModeBar': False})
            with r1[2]: st.write("Fremadrettet"); st.plotly_chart(create_donut_chart(158, "Frem"), config={'displayModeBar': False})
            with r1[3]: st.write("Progressive"); st.plotly_chart(create_donut_chart(77, "Prog"), config={'displayModeBar': False})
            
            r2 = st.columns(4)
            with r2[0]: st.write("Lange pasninger"); st.plotly_chart(create_donut_chart(22, "Lange"), config={'displayModeBar': False})
            with r2[1]: st.write("Sidste 1/3"); st.plotly_chart(create_donut_chart(68, "1/3"), config={'displayModeBar': False})
            with r2[2]: st.write("Off. Aktioner"); st.plotly_chart(create_donut_chart(0, "Off"), config={'displayModeBar': False})
            with r2[3]: st.write("Off. Dueller"); st.plotly_chart(create_donut_chart(235, "Duel"), config={'displayModeBar': False})

            r3 = st.columns(4)
            with r3[0]: st.write("Erobringer"); st.plotly_chart(create_donut_chart(87, "Erob"), config={'displayModeBar': False})
            with r3[1]: st.write("Modst. bane"); st.plotly_chart(create_donut_chart(57, "Bane"), config={'displayModeBar': False})
            with r3[2]: st.write("Generobringer"); st.plotly_chart(create_donut_chart(51, "Gen"), config={'displayModeBar': False})
            with r3[3]: st.write("Interceptions"); st.plotly_chart(create_donut_chart(31, "Int"), config={'displayModeBar': False})

    # --- TAB 2: SPILLERAKTIONER (DEN GAMLE "SPILLERPROFIL") ---
    with t_pitch:
        descriptions = {
            "Heatmap": "Bevægelsesmønster og intensitet på banen.",
            "Berøringer": "Alle aktioner med boldkontakt.",
            "Afslutninger": "Skudforsøg (Mål = rød firkant).",
            "Erobringer": "Tacklinger og interceptions."
        }
        touch_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
        df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
        akt_stats = pd.DataFrame()
        if not df_filtreret.empty:
            akt_stats = df_filtreret.groupby('Action_Label').agg(Total=('OUTCOME', 'count'), Succes=('OUTCOME', 'sum')).sort_values('Total', ascending=False)

        c_stats_side, c_buffer, c_pitch_side = st.columns([1, 0.05, 2.2])

        with c_stats_side:
            st.markdown(f'<div class="player-header">{valgt_spiller}</div>', unsafe_allow_html=True)
            # Hurtige metrics
            m_col1, m_col2 = st.columns(2)
            m_col1.metric("Aktioner", len(df_spiller))
            m_col2.metric("Pasning %", f"{pas_acc}%")
            
            st.markdown("<hr>", unsafe_allow_html=True)
            st.write("**Top Aktioner**")
            if not akt_stats.empty:
                for akt, row in akt_stats.head(8).iterrows():
                    st.markdown(f"<div style='font-size:12px; display:flex; justify-content:space-between; border-bottom:1px solid #f0f0f0; padding:3px 0;'><span>{akt}</span><b>{int(row['Total'])}</b></div>", unsafe_allow_html=True)

        with c_pitch_side:
            visning = st.segmented_control("Vælg lag", options=list(descriptions.keys()), default="Heatmap")
            
            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, CURRENT_SEASON, visning)

            df_plot = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
            if not df_plot.empty:
                if visning == "Heatmap":
                    pitch.kdeplot(df_plot.EVENT_X, df_plot.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                elif visning == "Berøringer":
                    d = df_plot[df_plot['EVENT_TYPEID'].isin(touch_ids)]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='#003366', s=40, edgecolors='white', alpha=0.5)
                elif visning == "Afslutninger":
                    d = df_plot[df_plot['EVENT_TYPEID'].isin([13, 14, 15, 16])]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='red', s=100, marker='s')
                elif visning == "Erobringer":
                    d = df_plot[df_plot['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='orange', s=100)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 3: FYSISK DATA ---
    with t_phys:
        df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)
        if df_phys is not None and not df_phys.empty:
            latest = df_phys.iloc[0]
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Distance", f"{round(latest['DISTANCE']/1000, 2)} km")
            m2.metric("HSR", f"{int(latest['HSR'])} m")
            m3.metric("Topfart", f"{round(latest['TOP_SPEED'], 1)} km/t")
            m4.metric("HI Runs", int(latest['HI_RUNS']))
            
            # Plotly bar chart
            df_phys = df_phys.sort_values('MATCH_DATE')
            fig_phys = go.Figure(go.Bar(x=df_phys['MATCH_DATE'], y=df_phys['HSR'], marker_color='#cc0000'))
            fig_phys.update_layout(title="HSR meter pr. kamp", height=300, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_phys, use_container_width=True)

if __name__ == "__main__":
    vis_side()
