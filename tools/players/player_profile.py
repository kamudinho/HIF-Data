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
    """Tegner info-boksen på banen præcis som i den tidligere fungerende version"""
    ax.add_patch(plt.Rectangle((1, 82), 40, 16, color='#003366', alpha=0.9, zorder=10))
    ax.text(12, 94, player_name.upper(), color='white', fontsize=11, fontweight='bold', zorder=11)
    ax.text(12, 89, f"{season} | {view_name}", color='white', fontsize=9, alpha=0.8, zorder=11)
    if logo:
        logo_arr = np.array(logo.convert("RGBA"))
        newax = ax.inset_axes([0.02, 0.84, 0.08, 0.12], zorder=12)
        newax.imshow(logo_arr)
        newax.axis('off')

def create_relative_donut(player_val, max_val, label, color="#003366"):
    """Donut med overskrift inkluderet i layout"""
    base_max = max(max_val, player_val, 1)
    remainder = max(0, base_max - player_val)
    fig = go.Figure(go.Pie(
        values=[player_val, remainder],
        hole=0.72,
        marker_colors=[color, "#EEEEEE"],
        textinfo='none',
        hoverinfo='none'
    ))
    pct = int((player_val / base_max) * 100) if base_max > 0 else 0
    fig.update_layout(
        title={'text': f"<b>{label}</b>", 'y':0.9, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': {'size': 14}},
        showlegend=False, margin=dict(t=40, b=10, l=10, r=10), height=180, width=150,
        annotations=[dict(text=f"{player_val}<br><span style='font-size:10px;'>{pct}%</span>", 
                     x=0.5, y=0.5, font_size=15, showarrow=False, font_family="Arial Black")]
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
    spiller_liste = sorted([s for s in df_all['VISNINGSNAVN'].unique() if s is not None])
    
    with col_h_spiller:
        valgt_spiller = st.selectbox("Spiller", spiller_liste, label_visibility="collapsed")
        df_spiller = df_all[df_all['VISNINGSNAVN'] == valgt_spiller].copy()
        valgt_player_uuid = df_spiller['PLAYER_OPTAUUID'].iloc[0]

    df_phys = get_physical_data(valgt_spiller, valgt_player_uuid, valgt_hold, conn)

    # --- TABS ---
    t_profile, t_pitch, t_phys, t_stats, t_compare = st.tabs(["Profil", "Aktioner", "Fysisk", "Statistik", "Sammenligning"])

    with t_profile:
        col_card, col_main = st.columns([1, 3.5])
        with col_card:
            maal = len(df_spiller[df_spiller['EVENT_TYPEID'] == 16])
            assists = len(df_spiller[df_spiller['QUALIFIERS'].fillna('').str.contains('154')])
            st.markdown(f"""<div style='background:#003366;color:white;padding:20px;border-radius:10px;text-align:center;'>
                <h3 style='margin:0;'>{valgt_spiller}</h3><p style='opacity:0.8;'>{SEASONNAME}</p><hr>
                <p style='font-size:20px;margin:10px 0;'>Mål: <b>{maal}</b></p>
                <p style='font-size:20px;margin:10px 0;'>Assists: <b>{assists}</b></p></div>""", unsafe_allow_html=True)
        
        with col_main:
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
            c4.plotly_chart(create_relative_donut(s_val['a'], truppen['a'].max(), "Totale Aktioner", "#FFD700"), config={'displayModeBar': False})

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
        if df_phys is not None and not df_phys.empty:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Gns. Distance", f"{round(df_phys['DISTANCE'].mean()/1000, 2)} km")
            m2.metric("Gns. HSR", f"{int(df_phys['HSR'].mean())} m")
            m3.metric("Gns. Sprints", f"{int(df_phys['SPRINTING'].mean())} m")
            m4.metric("Top Speed", f"{round(df_phys['TOP_SPEED'].max(), 1)} km/h")
            
            st.write("---")
            fig_dist = go.Figure(go.Bar(x=df_phys['MATCH_DATE'], y=df_phys['DISTANCE'], marker_color='#003366'))
            fig_dist.update_layout(title="Total distance pr. kamp (meter)", height=350, margin=dict(t=50, b=20))
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.info("Ingen fysiske data tilgængelige for perioden.")

    with t_stats:
        st.subheader("Fordeling af aktioner")
        stats_df = df_spiller['Action_Label'].value_counts().reset_index()
        stats_df.columns = ['Aktionstype', 'Antal']
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

    with t_compare:
        st.subheader("Sammenligning")
        modstander = st.selectbox("Vælg spiller at sammenligne med", [s for s in spiller_liste if s != valgt_spiller])
        df_comp = df_all[df_all['VISNINGSNAVN'] == modstander]
        
        c_left, c_right = st.columns(2)
        with c_left:
            st.write(f"**{valgt_spiller}**")
            st.write(f"Antal aktioner: {len(df_spiller)}")
        with c_right:
            st.write(f"**{modstander}**")
            st.write(f"Antal aktioner: {len(df_comp)}")

if __name__ == "__main__":
    vis_side()
