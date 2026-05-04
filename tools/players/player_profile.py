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

def draw_player_info_box(ax, logo, player_name, season, view_name):
    """Tegner en info-boks i hjørnet af fodboldbanen"""
    # Baggrundsboks
    ax.add_patch(plt.Rectangle((1, 85), 35, 14, alpha=0.9, zorder=10))
    # Spillertekst
    ax.text(12, 95, player_name.upper(), color='black', fontsize=10, fontweight='bold', zorder=11)
    ax.text(12, 91, f"{season} | {view_name}", color='black', fontsize=8, alpha=0.8, zorder=11)
    # Logo hvis det findes
    if logo:
        # Konverter PIL Image til array for matplotlib
        logo_arr = np.array(logo)
        newax = ax.inset_axes([0.02, 0.87, 0.08, 0.1], zorder=12)
        newax.imshow(logo_arr)
        newax.axis('off')

def create_team_donut(player_val, team_total, label, color="#003366"):
    """
    Viser spillerens andel af holdets samlede præstation.
    Hvis team_total er 0, bruges 100 som baseline for procenter.
    """
    if team_total <= 0: team_total = max(player_val, 1)
    
    # Beregn restværdi for at fylde cirklen ud
    remainder = max(0, team_total - player_val)
    
    fig = go.Figure(go.Pie(
        values=[player_val, remainder],
        hole=0.7,
        marker_colors=[color, "#EEEEEE"],
        textinfo='none',
        hoverinfo='none'
    ))
    
    # Beregn procentvis andel til center-tekst
    pct = int((player_val / team_total) * 100) if team_total > 0 else 0
    
    fig.update_layout(
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        height=130,
        width=130,
        annotations=[dict(
            text=f"{player_val}<br><span style='font-size:10px;'>{pct}%</span>", 
            x=0.5, y=0.5, font_size=16, showarrow=False, font_family="Arial Black"
        )]
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

def vis_side(dp=None):
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 16px !important; text-align: center; font-weight: bold !important; width: 100%; }
        [data-testid="stMetricLabel"] { font-size: 10px !important; text-align: center; width: 100%; }
        .profile-card { background-color: #003366; color: white; padding: 15px; border-radius: 12px; }
        </style>
        """, unsafe_allow_html=True)

    conn = _get_snowflake_conn()
    if not conn: return

    # --- TOP-MENU KONFIGURATION (Løser 'hold_logo' fejlen & skubber dropdowns til højre) ---
    df_teams_raw = conn.query(f"SELECT DISTINCT CONTESTANTHOME_NAME, CONTESTANTHOME_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID IN {LIGA_IDS}")
    mapping_lookup = {str(info['opta_uuid']).lower().replace('t', ''): name for name, info in TEAMS.items() if 'opta_uuid' in info}
    
    # team_map must be defined before selectbox can use it
    team_map = {mapping_lookup[str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','')]: r['CONTESTANTHOME_OPTAUUID'] 
                for _, r in df_teams_raw.iterrows() if str(r['CONTESTANTHOME_OPTAUUID']).lower().replace('t','') in mapping_lookup}

    # Definer kolonnerne [1, 2.5, 1.2, 1.2] for at få dropdowns til højre
    col_logo, col_spacer_mid, col_h_hold, col_h_spiller = st.columns([1, 2.5, 1.2, 1.2])

    with col_h_hold:
        valgt_hold = st.selectbox("Hold", sorted(list(team_map.keys())), label_visibility="collapsed")
        valgt_uuid_hold = team_map[valgt_hold]
    
    # HENT OG VIS LOGOET HER (Løftet op på højde med dropdowns)
    hold_logo = get_logo_img(valgt_uuid_hold)
    with col_logo:
        if hold_logo:
            st.image(hold_logo, width=85)

    # 1. HENT DATA MED ACTION_LABEL
    with st.spinner("Henter spillerdata..."):
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
        
        if df_all is not None and not df_all.empty:
            df_all['qual_list'] = df_all['QUALIFIERS'].fillna('').str.split(',')
            df_all['Action_Label'] = df_all.apply(get_action_label, axis=1)

    spiller_liste = sorted(df_all['VISNINGSNAVN'].unique())
    
    with col_h_spiller:
        valgt_spiller = st.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
        valgt_player_uuid = df_all[df_all['VISNINGSNAVN'] == valgt_spiller]['PLAYER_OPTAUUID'].iloc[0]
        df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()

    # 3. HENT FYSISK DATA (Flyttet herop for at undgå 'local variable' fejl)
    df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    # --- TABS (Placeret under dropdowns/logo) ---
    t_profile, t_pitch, t_phys, t_stats, t_compare = st.tabs([
        "Spillerprofil", "Spilleraktioner", "Fysisk data", "Statistik", "Sammenligning"
    ])
    
    # --- TAB INDHOLD ---
    with t_profile:
        # Her definerer vi col_card (venstre) og col_main (højre) inde i fanen
        col_card, col_main = st.columns([1, 3.5])
        
        with col_card:
            # Beregn værdier dynamisk for den valgte spiller
            antall_kampe = 0
            total_minutter = 0
            
            if df_phys is not None and not df_phys.empty:
                df_phys['MATCH_DATE'] = pd.to_datetime(df_phys['MATCH_DATE'])
                antall_kampe = df_phys['MATCH_DATE'].nunique()
                total_minutter = int(pd.to_numeric(df_phys['MINUTES'], errors='coerce').sum())
                
            maal = len(df_spiller[df_spiller['EVENT_TYPEID'] == 16])
            # 154 er Opta Qualifier for Assist
            assists = len(df_spiller[df_spiller['QUALIFIERS'].fillna('').str.contains('154')]) 

            # Den blå boks (uden logo, da det er flyttet op)
            st.markdown(f"""
                <div class="profile-card">
                    <h5 style='margin:0;'>{valgt_spiller}</h5>
                    <p style='margin:0; opacity:0.8;'>Sæson: {CURRENT_SEASON}</p>
                    <hr style='border-color: rgba(255,255,255,0.2);'>
                    <table style='width:100%; font-size:14px;'>
                        <tr><td>Kampe:</td><td style='text-align:right;'><b>{antall_kampe}</b></td></tr>
                        <tr><td>Minutter:</td><td style='text-align:right;'><b>{total_minutter}</b></td></tr>
                        <tr><td>Mål:</td><td style='text-align:right;'><b>{maal}</b></td></tr>
                        <tr><td>Assists:</td><td style='text-align:right;'><b>{assists}</b></td></tr>
                    </table>
                </div>
            """, unsafe_allow_html=True)
            
            # (Resten af volumen-bars koden lander her...)
            st.write("")
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
            st.markdown("<h4 style='text-align:center; color:#003366;'>Spillerstatistik</h4>", unsafe_allow_html=True)
            
            # Beregn værdier fra data for Donuts
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
                
    with t_pitch:
        descriptions = {
            "Heatmap": "Viser spillerens generelle bevægelsesmønster og intensitet på banen.",
            "Berøringer": "Alle aktioner hvor spilleren har været i kontakt med bolden.",
            "Afslutninger": "Oversigt over alle skudforsøg (Mål markeres med stjerne).",
            "Erobringer": "Tacklinger, bolderobringer og opsnappede afleveringer."
        }
        touch_ids = [1, 3, 7, 10, 11, 12, 13, 14, 15, 16, 42, 44, 49, 50, 51, 54, 61, 73]
        df_filtreret = df_spiller[~df_spiller['Action_Label'].isin(['Pasning', 'Indkast'])]
        akt_stats = pd.DataFrame()
        if not df_filtreret.empty:
            akt_stats = df_filtreret.groupby('Action_Label').agg(Total=('OUTCOME', 'count'), Succes=('OUTCOME', 'sum')).sort_values('Total', ascending=False)

        c_stats_side, c_buffer, c_pitch_side = st.columns([1, 0.05, 2.2])

        with c_stats_side:
            total_akt = len(df_spiller)
            pas_df = df_spiller[df_spiller['EVENT_TYPEID'] == 1]
            pas_count = len(pas_df)
            pas_acc = (pas_df['OUTCOME'].sum() / pas_count * 100) if pas_count > 0 else 0
            chancer_skabt = akt_stats[akt_stats.index.str.contains("Key Pass|assist|Stor chance", case=False, na=False)]['Total'].sum() if not akt_stats.empty else 0
            shots_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([13, 14, 15, 16])])
            cross_count = len(df_spiller[df_spiller['qual_list'].apply(lambda x: "2" in x if isinstance(x, list) else False)])
            erob_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin([7, 8, 12, 49])])
            touch_count = len(df_spiller[df_spiller['EVENT_TYPEID'].isin(touch_ids)])

            m_r1 = st.columns(4)
            m_r1[0].metric("Aktioner", total_akt)
            m_r1[1].metric("Berøringer", touch_count)
            m_r1[2].metric("Pasninger", pas_count)
            m_r1[3].metric("Pasning %", f"{int(pas_acc)}%")
            m_r2 = st.columns(4)
            m_r2[0].metric("Skud", shots_count)
            m_r2[1].metric("Chancer", int(chancer_skabt))
            m_r2[2].metric("Indlæg", cross_count)
            m_r2[3].metric("Erobringer", erob_count)

            st.markdown("<hr style='margin: 15px 0; opacity: 0.5;'>", unsafe_allow_html=True)
            st.write("**Top 10: Aktioner**")
            if not akt_stats.empty:
                bare_antal = ['Erobring', 'Clearing', 'Boldtab', 'Frispark vundet', 'Blokeret skud', 'Interception']
                for akt, row in akt_stats.head(10).iterrows():
                    total, succes = int(row['Total']), int(row['Succes'])
                    stats_html = f"<b>{total}</b>" if akt in bare_antal else f"{succes}/{total} <b>({int(succes/total*100)}%)</b>"
                    st.markdown(f'<div style="display:flex; justify-content:space-between; font-size:11px; border-bottom:0.5px solid #eee; padding:5px 0;"><span>{akt}</span><span style="font-family:monospace;">{stats_html}</span></div>', unsafe_allow_html=True)

        with c_pitch_side:
            c_side_spacer, c_desc_col, c_menu_col = st.columns([0.2, 2.0, 1.0])
            with c_menu_col:
                visning = st.selectbox("Visning", list(descriptions.keys()), key="pitch_view_sel", label_visibility="collapsed")
            with c_desc_col:
                st.markdown(f'<div style="text-align: right; margin-top: 8px; line-height: 1.2;"><span style="color: #666; font-size: 0.85rem;">{descriptions.get(visning)}</span></div>', unsafe_allow_html=True)

            pitch = Pitch(pitch_type='opta', pitch_color='#ffffff', line_color='#BDBDBD')
            fig, ax = pitch.draw(figsize=(10, 7))
            draw_player_info_box(ax, hold_logo, valgt_spiller, CURRENT_SEASON, visning)

            df_plot = df_spiller.dropna(subset=['EVENT_X', 'EVENT_Y'])
            if not df_plot.empty:
                if visning == "Heatmap":
                    pitch.kdeplot(df_plot.EVENT_X, df_plot.EVENT_Y, ax=ax, cmap='Blues', fill=True, alpha=0.6, levels=50)
                elif visning == "Berøringer":
                    d = df_plot[df_plot['EVENT_TYPEID'].isin(touch_ids)]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='#084594', s=40, edgecolors='white', alpha=0.5)
                elif visning == "Afslutninger":
                    d = df_plot[df_plot['EVENT_TYPEID'].isin([13, 14, 15, 16])]
                    goals = d[d['EVENT_TYPEID'] == 16]; misses = d[d['EVENT_TYPEID'].isin([13, 14, 15])]
                    ax.scatter(misses.EVENT_X, misses.EVENT_Y, color='grey', s=60, edgecolors='black', alpha=0.7)
                    ax.scatter(goals.EVENT_X, goals.EVENT_Y, color='red', s=120, marker='s', edgecolors='black', zorder=5)
                elif visning == "Erobringer":
                    d = df_plot[df_plot['EVENT_TYPEID'].isin([7, 8, 12, 49])]
                    ax.scatter(d.EVENT_X, d.EVENT_Y, color='orange', s=100, edgecolors='white')
            st.pyplot(fig, use_container_width=True)

    with t_phys:
        df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)
        if df_phys is not None and not df_phys.empty:
            df_phys['MATCH_DATE'] = pd.to_datetime(df_phys['MATCH_DATE'])
            df_phys = df_phys.sort_values('MATCH_DATE', ascending=False)
            avg_dist = df_phys['DISTANCE'].mean()
            avg_hsr = df_phys['HSR'].mean()
            latest = df_phys.iloc[0]

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Seneste Distance", f"{round(latest['DISTANCE']/1000, 2)} km", delta=f"{round((latest['DISTANCE'] - avg_dist)/1000, 2)} km")
            m2.metric("HSR Meter", f"{int(latest['HSR'])} m", delta=f"{int(latest['HSR'] - avg_hsr)} m")
            m3.metric("Topfart", f"{round(latest['TOP_SPEED'], 1)} km/t")
            m4.metric("Højintense Akt.", int(latest['HI_RUNS']))

            t_sub_log, t_sub_charts = st.tabs(["Kampoversigt", "Grafer"])

            with t_sub_charts:
                cat_choice = st.segmented_control("Vælg metrik", options=["HSR (m)", "Sprint (m)", "Distance (km)", "Topfart (km/t)"], default="HSR (m)", key="phys_graph_control")
                mapping = {"HSR (m)": ("HSR", 1, "m"), "Sprint (m)": ("SPRINTING", 1, "m"), "Distance (km)": ("DISTANCE", 1000, "km"), "Topfart (km/t)": ("TOP_SPEED", 1, "km/t")}
                col, div, suffix = mapping[cat_choice]

                df_chart = df_phys[df_phys['MATCH_DATE'] >= '2025-07-01'].copy()
                df_chart = df_chart.drop_duplicates(subset=['MATCH_DATE', 'MATCH_TEAMS'])
                df_chart = df_chart.sort_values('MATCH_DATE', ascending=True)

                if not df_chart.empty:
                    def get_opponent(teams_str, my_team):
                        if not teams_str: return "?"
                        parts = [p.strip() for p in teams_str.split('-')]
                        if len(parts) < 2: return teams_str
                        return parts[1] if parts[0].lower() in my_team.lower() else parts[0]

                    df_chart['Opponent'] = df_chart['MATCH_TEAMS'].apply(lambda x: get_opponent(x, valgt_hold))
                    df_chart['Label'] = df_chart['Opponent'] + "<br>" + df_chart['MATCH_DATE'].dt.strftime('%d/%m')
                    y_vals = df_chart[col] / div
                    season_avg = y_vals.mean()

                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_chart['Label'], 
                        y=y_vals,
                        text=y_vals.apply(lambda x: f"{x:.0f}" if x > 100 else f"{x:.1f}"),
                        textposition='outside', 
                        marker_color='#cc0000', 
                        textfont=dict(size=9, color="black"),
                        cliponaxis=False
                    ))

                    fig.add_shape(type="line", x0=-0.5, x1=len(df_chart)-0.5, y0=season_avg, y1=season_avg, 
                                 line=dict(color="#D3D3D3", width=2, dash="dash"))

                    fig.update_layout(
                        plot_bgcolor="white", 
                        height=400, 
                        margin=dict(t=50, b=80, l=10, r=10),
                        xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=10), type='category'),
                        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', showticklabels=False, zeroline=False, range=[0, y_vals.max() * 1.3]),
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Ingen fysiske data fundet for denne sæson.")

            with t_sub_log:
                st.data_editor(df_phys, hide_index=True, use_container_width=True, disabled=True)

if __name__ == "__main__":
    vis_side()
