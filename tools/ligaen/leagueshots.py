import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS, TEAM_COLORS, SEASONS, COMPETITIONS
from data.data_load import _get_snowflake_conn
from data.players.player_mapping import player_mapping
from utils.pitches import get_pitch, get_boundaries
from PIL import Image
import requests
from io import BytesIO

# --- KONFIGURATION (Hvidovre-app værdier) ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"

# --- ZONE DEFINITIONER ---
ZONE_BOUNDARIES = get_boundaries()

@st.cache_data(ttl=3600)
def load_league_data(liga_uuid):
    conn = _get_snowflake_conn()
    if not conn or not liga_uuid: return pd.DataFrame()
    
    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{liga_uuid}'"
    
    sql = f"""
        SELECT 
            e.*, 
            TRIM(l.FIRST_NAME) || ' ' || TRIM(l.LAST_NAME) as FULL_PLAYER_NAME,
            q.QUALIFIER_VALUE as XG_RAW 
        FROM {DB}.OPTA_EVENTS e 
        LEFT JOIN (
            SELECT DISTINCT MATCH_OPTAUUID, PLAYER_OPTAUUID, FIRST_NAME, LAST_NAME 
            FROM {DB}.OPTA_MATCH_LINEUPS 
            WHERE FIRST_NAME IS NOT NULL AND LAST_NAME IS NOT NULL
        ) l 
            ON e.MATCH_OPTAUUID = l.MATCH_OPTAUUID AND e.PLAYER_OPTAUUID = l.PLAYER_OPTAUUID
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 321
        WHERE e.EVENT_TYPEID IN (13,14,15,16) 
        AND e.MATCH_OPTAUUID IN ({match_sql})
    """
    
    try:
        df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        df.columns = [c.upper() for c in df.columns]

        df = resolve_player_names(df, conn)

        return df
    except Exception as e:
        st.error(f"Fejl ved indlæsning af data fra Snowflake: {e}")
        return pd.DataFrame()


def resolve_player_names(df, conn=None):
    """
    Udfylder PLAYER_NAME på df ved brug af player_mapping (data/players/player_mapping.py).

    Rækkefølge:
      1. Statisk liste i player_mapping (optauuid_to_name) — hurtigst, ingen DB-kald.
      2. FULL_PLAYER_NAME fra OPTA_MATCH_LINEUPS-joinet (allerede hentet i SQL'en ovenfor).
      3. Ét live DB-opslag pr. unikt resterende UUID via player_mapping.get_name_by_opta_uuid.
      4. Alt der stadig mangler navn -> "Ukendt".

    Nyligt fundne navne caches automatisk tilbage i player_mapping, så fremtidige
    kald (i denne session) slipper for at slå dem op igen.
    """
    if df.empty or 'PLAYER_OPTAUUID' not in df.columns:
        if 'PLAYER_NAME' not in df.columns:
            df['PLAYER_NAME'] = "Ukendt"
        else:
            df['PLAYER_NAME'] = df['PLAYER_NAME'].fillna("Ukendt")
        return df

    # 1. Statisk mapping (vektoriseret opslag, ingen DB-kald)
    resolved = df['PLAYER_OPTAUUID'].map(player_mapping.optauuid_to_name)

    # 2. Fald tilbage på navnet fra lineup-joinet, hvis den statiske liste ikke kender spilleren
    if 'FULL_PLAYER_NAME' in df.columns:
        resolved = resolved.fillna(df['FULL_PLAYER_NAME'])

    df['PLAYER_NAME'] = resolved

    # 3. For de resterende ukendte: ét live-opslag pr. unikt UUID (ikke pr. række)
    missing_mask = df['PLAYER_NAME'].isna() | (df['PLAYER_NAME'].astype(str).str.strip() == '')
    missing_uuids = df.loc[missing_mask, 'PLAYER_OPTAUUID'].dropna().unique()

    if len(missing_uuids) > 0 and conn is not None:
        for uuid in missing_uuids:
            navn = player_mapping.get_name_by_opta_uuid(uuid, conn=conn, db_name=DB)
            if navn and navn != "Ukendt":
                df.loc[df['PLAYER_OPTAUUID'] == uuid, 'PLAYER_NAME'] = navn

    # 4. Sidste fallback
    df['PLAYER_NAME'] = df['PLAYER_NAME'].fillna("Ukendt")
    df.loc[df['PLAYER_NAME'].astype(str).str.strip() == '', 'PLAYER_NAME'] = "Ukendt"

    # Cache nye navne tilbage i player_mapping til senere brug i sessionen
    player_mapping.register_players_from_df(df, uuid_col='PLAYER_OPTAUUID', name_col='PLAYER_NAME')

    return df

@st.cache_data(ttl=3600)
def get_logo_img(url):
    try: return Image.open(BytesIO(requests.get(url, timeout=5).content))
    except: return None

def to_metric(val, total_m):
    return val * (total_m / 100)

def map_to_zone(r):
    mx, my = to_metric(r['EVENT_X'], 105), to_metric(r['EVENT_Y'], 68)
    for z, b in ZONE_BOUNDARIES.items():
        if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]: return z
    return "Zone 8"

def draw_logo_on_pitch(ax, logo_img):
    if logo_img:
        ax_logo = ax.inset_axes([0.02, 0.89, 0.12, 0.10], transform=ax.transAxes)
        ax_logo.imshow(logo_img)
        ax_logo.axis('off')

# --- MAIN APP ---
def vis_side(dp=None):
    st.markdown("""
    <style>
        header {visibility: hidden;}
        .main .block-container { 
            padding-top: 1rem !important; 
            padding-bottom: 3rem !important; 
            max-width: 1400px !important; 
        }
        .stat-box { 
            background-color: #f8f9fa; 
            padding: 10px !important; 
            border-radius: 5px; 
            border-left: 5px solid #cc0000; 
            margin-bottom: 15px !important; 
            display: block; 
        }
        .stat-label { font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; }
        .stat-value { font-size: 1.3rem; font-weight: 800; color: #1a1a1a; margin-top: 3px; }
    </style>
    """, unsafe_allow_html=True)

    top_col1, top_col2 = st.columns([1.5, 2.5])
    
    with top_col1:
        st.caption("**Afslutningsanalyse**")

    f_col1, f_col2, f_col3 = top_col2.columns(3)
    with f_col1:
        sæson_sel = st.selectbox("Sæson", list(SEASONS.keys()), index=0)
    
    with f_col2:
        tilgængelige_turneringer = [t for t in SEASONS[sæson_sel].keys() if "superliga" not in t.lower()]
        if not tilgængelige_turneringer:
            tilgængelige_turneringer = list(SEASONS[sæson_sel].keys())
        turnering_sel = st.selectbox("Turnering", tilgængelige_turneringer, index=0)

    from data.utils.team_mapping import SEASON_LEAGUE_MAPPER
    teams = SEASON_LEAGUE_MAPPER.get(sæson_sel, {}).get(turnering_sel, sorted(list(TEAMS.keys())))

    with f_col3:
        default_idx = teams.index("Hvidovre") if "Hvidovre" in teams else 0
        t_sel = st.selectbox("Hold", teams, index=default_idx)

    aktuel_liga_uuid = SEASONS[sæson_sel][turnering_sel]
    df_all = load_league_data(aktuel_liga_uuid)
    
    if not df_all.empty and 'EVENT_CONTESTANT_OPTAUUID' in df_all.columns:
        uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
        df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    else:
        if not df_all.empty:
            df_all['KLUB_NAVN'] = None

    if df_all.empty or not teams or t_sel == "Der er ingen data at vise":
        st.warning("Ingen data at vise for den valgte sæson/turnering.")
        return

    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    if df_team.empty:
        st.warning(f"Der er ingen data at vise for {t_sel} i den valgte turnering.")
        return

    df_team['X_M'] = df_team['EVENT_X'].apply(lambda x: to_metric(x, 105))
    df_team['Y_M'] = df_team['EVENT_Y'].apply(lambda y: to_metric(y, 68))
    df_team['Zone'] = df_team.apply(map_to_zone, axis=1)
    
    df_team['IS_DZ'] = (df_team['X_M'] >= 88.5) & (df_team['Y_M'] >= 25.16) & (df_team['Y_M'] <= 42.84)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-ANALYSE", "SKUDZONER", "MÅLZONER"])

    # TAB 0: SPILLEROVERSIGT
    with tabs[0]:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        p_stats = []
        for p, d in df_team.groupby('PLAYER_NAME'):
            s, m = len(d), len(d[d['EVENT_TYPEID']==16])
            dz_d = d[d['IS_DZ']]
            dz_s, dz_m = len(dz_d), len(dz_d[dz_d['EVENT_TYPEID']==16])
            
            p_stats.append({
                "Spiller": p, 
                "Skud": s, 
                "Mål": m, 
                "Konv.%": (m/s*100 if s > 0 else 0),
                "DZ-Skud": dz_s,
                "DZ-Mål": dz_m,
                "DZ-Konv.%": (dz_m/dz_s*100 if dz_s > 0 else 0),
                "DZ-Andel": (dz_s / s * 100 if s > 0 else 0) 
            })

        df_display = pd.DataFrame(p_stats).sort_values("Konv.%", ascending=False)
        dynamic_height = (len(df_display) + 1) * 38 + 50

        st.dataframe(
            df_display,
            use_container_width=True, 
            hide_index=True,
            height=dynamic_height,
            column_config={
                "Spiller": st.column_config.TextColumn("Spiller", width="medium"),
                "DZ-Andel": st.column_config.ProgressColumn(
                    "DZ-Andel", 
                    help="Andel af skud foretaget i Danger Zone", 
                    format="%d%%", 
                    min_value=0, 
                    max_value=100,
                    width="medium"
                ),
                "Konv.%": st.column_config.NumberColumn("Konv.%", format="%.1f%%", width="small"),
                "DZ-Konv.%": st.column_config.NumberColumn("DZ-Konv.%", format="%.1f%%", width="small")
            }
        )
        
    # TAB 1: AFSLUTNINGER
    with tabs[1]:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([2, 1])
        t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
        t_logo = get_logo_img(TEAMS.get(t_sel, {}).get('logo'))
        with c2:
            p_sel = st.selectbox("Filtrer spiller", ["Alle spillere"] + sorted(df_team['PLAYER_NAME'].unique()))
            d_v = df_team if p_sel == "Alle spillere" else df_team[df_team['PLAYER_NAME'] == p_sel]
            s, m = len(d_v), len(d_v[d_v["EVENT_TYPEID"]==16])
            
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Konvertering</div><div class="stat-value">{(m/s*100 if s>0 else 0):.1f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch, fig, ax = get_pitch("halv", t_color=t_color)
            pitch.scatter(d_v['X_M'], d_v['Y_M'], s=100, c=(d_v['EVENT_TYPEID']==16).map({True: t_color, False: 'white'}), edgecolors=t_color, ax=ax, zorder=3)
            draw_logo_on_pitch(ax, t_logo); st.pyplot(fig)

    # TAB 2: DZ-ANALYSE
    with tabs[2]:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        c1, c2 = st.columns([2, 1])
        dz_d = df_team[df_team['IS_DZ']]
        t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
        t_logo = get_logo_img(TEAMS.get(t_sel, {}).get('logo'))
        with c2:
            s_dz, m_dz = len(dz_d), len(dz_d[dz_d["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Skud</div><div class="stat-value">{s_dz}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Mål</div><div class="stat-value">{m_dz}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Konv.</div><div class="stat-value">{(m_dz/s_dz*100 if s_dz>0 else 0):.1f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch, fig, ax = get_pitch("halv", t_color=t_color)
            ax.add_patch(patches.Rectangle((25.16, 88.7), 17.68, 16.5, color=t_color, alpha=0.15, zorder=1))
            pitch.scatter(dz_d['X_M'], dz_d['Y_M'], s=100, c=(dz_d['EVENT_TYPEID']==16).map({True: t_color, False: 'white'}), edgecolors=t_color, ax=ax, zorder=3)
            draw_logo_on_pitch(ax, t_logo); st.pyplot(fig)

    # TAB 3 & 4: ZONER (Skudzoner & Målzoner)
    for i, is_goal in enumerate([False, True]):
        with tabs[i+3]:
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            c1, c2 = st.columns([1.6, 1])
            plot_df = df_team[df_team['EVENT_TYPEID'] == 16] if is_goal else df_team
            total_count = len(plot_df)
            t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
            t_logo = get_logo_img(TEAMS.get(t_sel, {}).get('logo'))
            
            with c2:
                st.write(f"**Zone-stats ({'Mål' if is_goal else 'Skud'})**")
                z_summary = []
                for z, b in ZONE_BOUNDARIES.items():
                    z_d = plot_df[plot_df['Zone'] == z]
                    if len(z_d) > 0:
                        top_p = z_d['PLAYER_NAME'].value_counts().idxmax()
                        z_summary.append({"Zone": z, "Antal": len(z_d), "Andel": (len(z_d)/total_count if total_count > 0 else 0), "Topscorer": top_p})
                
                if z_summary:
                    st.dataframe(pd.DataFrame(z_summary).sort_values("Antal", ascending=False), hide_index=True, use_container_width=True, column_config={"Andel": st.column_config.NumberColumn(format="%.1f%%")})
            
            with c1:
                zone_counts = {z: len(plot_df[plot_df['Zone'] == z]) for z in ZONE_BOUNDARIES.keys()}
                pitch, fig, ax = get_pitch("halv", zone_boundaries=ZONE_BOUNDARIES, zone_data=zone_counts, t_color=t_color)
                draw_logo_on_pitch(ax, t_logo)
                st.pyplot(fig)

if __name__ == "__main__":
    vis_side()
