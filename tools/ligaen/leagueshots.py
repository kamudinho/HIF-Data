import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn # Importerer din eksisterende forbindelse
from PIL import Image
import requests
from io import BytesIO

# --- KONFIGURATION & DESIGN ---
HIF_RED = '#cc0000'
DZ_COLOR = '#1f77b4'
DB = "KLUB_HVIDOVREIF.AXIS"
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" # NordicBet Liga som standard

# --- DATA LOADING ---
def load_data():
    conn = _get_snowflake_conn()
    if not conn:
        return pd.DataFrame()

    # Din specifikke liga-skud query (opta_league_shotevents + opta_shotevents kombineret for fuld liga-oversigt)
    # Vi fjerner e.EVENT_CONTESTANT_OPTAUUID != '{HIF_UUID}' for at få ALLE hold med i oversigten
    match_id_subquery = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    
    sql = f"""
        SELECT e.*, q.QUALIFIER_VALUE as XG_RAW 
        FROM {DB}.OPTA_EVENTS e 
        LEFT JOIN {DB}.OPTA_QUALIFIERS q 
            ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID 
            AND q.QUALIFIER_QID = 321
        WHERE e.EVENT_TYPEID IN (13,14,15,16) 
        AND e.MATCH_OPTAUUID IN ({match_id_subquery})
    """
    
    with st.spinner("Henter ligadata fra Snowflake..."):
        df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
        return df

# --- LOGO & FARVE UTILS ---
@st.cache_data(ttl=3600)
def get_logo_img(url):
    try:
        response = requests.get(url, timeout=5)
        return Image.open(BytesIO(response.content))
    except:
        return None

def get_text_color(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return 'white' if luminance < 0.5 else 'black'

def get_team_style(team_name):
    color = HIF_RED
    logo_img = None
    if team_name in TEAM_COLORS:
        c = TEAM_COLORS[team_name]
        prim = c['primary'].lower()
        color = c.get('secondary', HIF_RED) if prim in ["#ffffff", "white", "#f9f9f9"] else c['primary']
    if team_name in TEAMS:
        url = TEAMS[team_name].get('logo')
        if url:
            logo_img = get_logo_img(url)
    return color, logo_img

def draw_logo_adjusted(ax, logo_img):
    if logo_img:
        ax_image = ax.inset_axes([0.08, 0.80, 0.12, 0.12], transform=ax.transAxes)
        ax_image.imshow(logo_img)
        ax_image.axis('off')

# --- MAIN APP ---
def vis_side(dp=None):
    st.markdown("""
        <style>
            .stTabs { margin-top: -30px; }
            [data-testid="stVerticalBlock"] > div:has(div.stColumns) { margin-bottom: -15px; }
        </style>
    """, unsafe_allow_html=True)

    # Hent data direkte via SQL hvis dp ikke indeholder det
    df_all = load_data()

    if df_all.empty:
        st.info("Ingen ligadata fundet i Snowflake.")
        return

    # 1. DATA PREP
    df_all.columns = [c.upper() for c in df_all.columns]
    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    
    # Filtrer hold der findes i TEAM_mapping
    teams_in_data = sorted([name for name in df_all['KLUB_NAVN'].unique() if pd.notna(name)])
    
    if not teams_in_data:
        st.warning("Data hentet, men kunne ikke matches med TEAM_mapping.")
        return

    # 2. HOLDVALG
    col_header1, col_header2 = st.columns([2, 1])
    with col_header2:
        # Finder index for Hvidovre hvis muligt
        hif_idx = teams_in_data.index("Hvidovre") if "Hvidovre" in teams_in_data else 0
        t_sel = st.selectbox("Vælg hold", teams_in_data, index=hif_idx, key="global_team_sel")
    
    with col_header1:
        st.caption(f"Afslutninger: {t_sel}")
        
    t_color, t_logo = get_team_style(t_sel)
    txt_color = get_text_color(t_color)

    # 3. ZONE LOGIK (Custom banestørrelse)
    P_L, P_W = 105.0, 68.0
    X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
    X_INN_L, X_INN_R = (P_W - 40.2) / 2, (P_W + 40.2) / 2
    Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0
    
    ZONE_BOUNDARIES = {
        "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 4A": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_R, "x_max": X_INN_R},
        "Zone 4B": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_INN_L, "x_max": X_MID_L},
        "Zone 5A": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_MID_R, "x_max": X_INN_R},
        "Zone 5B": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_INN_L, "x_max": X_MID_L},
        "Zone 6A": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": X_INN_R, "x_max": P_W},
        "Zone 6B": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": 0, "x_max": X_INN_L},
        "Zone 7C": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": 0, "x_max": X_MID_L},
        "Zone 7B": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 7A": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_R, "x_max": P_W},
        "Zone 8":  {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": P_W}
    }

    def map_to_zone(r):
        mx, my = r['EVENT_X'] * (P_L / 100), r['EVENT_Y'] * (P_W / 100)
        for z, b in ZONE_BOUNDARIES.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]:
                return z
        return "Zone 8"

    df_all['Zone'] = df_all.apply(map_to_zone, axis=1)
    df_all['IS_DZ_GEO'] = (df_all['EVENT_X'] >= 88.5) & (df_all['EVENT_Y'] >= 37.0) & (df_all['EVENT_Y'] <= 63.0)

    # 4. TABS
    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])
    
    # --- TAB 0: SPILLEROVERSIGT ---
    # --- TAB 0: SPILLEROVERSIGT ---
    # --- TAB 0: SPILLEROVERSIGT ---
    with tabs[0]:
        stats = []
        # Gruppér kun på spillere fra det valgte hold
        df_team_only = df_all[df_all['KLUB_NAVN'] == t_sel]
        
        for p, d in df_team_only.groupby('PLAYER_NAME'):
            dz = d[d['IS_DZ_GEO']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            dz_s, dz_m = len(dz), len(dz[dz['EVENT_TYPEID'] == 16])
            
            stats.append({
                "Spiller": p, 
                "Skud": s, 
                "Mål": m,  
                "Konv.%": (m/s*100) if s > 0 else 0.0,
                "DZ-Skud": dz_s, 
                "DZ-Mål": dz_m,
                "DZ-Konv.%": (dz_m/dz_s*100) if dz_s > 0 else 0.0,
                "DZ-Andel": (dz_s/s*100) if s > 0 else 0.0
            })
            
        df_f = pd.DataFrame(stats).sort_values("Skud", ascending=False)
        
        # Beregn højde så hele tabellen vises (ca. 35px pr række + header)
        dynamisk_hojde = (len(df_f) + 1) * 35 + 10
        
        # Konfiguration af kolonner: Formatering og centrering
        st.dataframe(
            df_f, 
            use_container_width=True, 
            height=dynamisk_hojde,
            hide_index=True,
            column_config={
                "Spiller": st.column_config.TextColumn("Spiller", width="medium"),
                "Skud": st.column_config.NumberColumn("Skud", format="%d"),
                "Mål": st.column_config.NumberColumn("Mål", format="%d"),
                "Konv.%": st.column_config.NumberColumn("Konv.%", format="%.2f%%"),
                "DZ-Skud": st.column_config.NumberColumn("DZ-Skud", format="%d"),
                "DZ-Mål": st.column_config.NumberColumn("DZ-Mål", format="%d"),
                "DZ-Konv.%": st.column_config.NumberColumn("DZ-Konv.%", format="%.2f%%"),
                "DZ-Andel": st.column_config.NumberColumn("DZ-Andel", format="%.2f%%")
            }
        )
        
        # CSS til at tvinge centrering af alt indhold i tabellen
        st.markdown("""
            <style>
                /* Centrerer tekst i alle celler i Streamlit Dataframes */
                [data-testid="stTable"] td { text-align: center !important; }
                [data-testid="stDataFrame"] div[data-testid="stTable"] div { text-align: center !important; }
                /* Sikrer at tal-kolonner også centreres */
                [data-testid="stDataFrame"] div[class*="StyledDataFrameDataCell"] { justify-content: center !important; text-align: center !important; }
            </style>
        """, unsafe_allow_html=True)
        
    # --- TAB 1: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            df_t = df_all[df_all['KLUB_NAVN'] == t_sel]
            p_sel = st.selectbox("Vælg spiller", ["Alle"] + sorted(df_t['PLAYER_NAME'].unique()), key="p1")
            d_v = df_t if p_sel == "Alle" else df_t[df_t['PLAYER_NAME'] == p_sel]
            st.metric("Antal skud", len(d_v))
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: t_color, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=50, c=colors, edgecolors=t_color, ax=ax, alpha=0.7)
            draw_logo_adjusted(ax, t_logo)
            st.pyplot(fig)

    # --- TAB 2: DZ-AFSLUTNINGER ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2:
            df_dz = df_all[(df_all['KLUB_NAVN'] == t_sel) & (df_all['IS_DZ_GEO'])]
            st.metric("DZ Skud", len(df_dz))
            st.caption("DZ = Danger Zone (Det centrale felt i feltet)")
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            colors = (df_dz['EVENT_TYPEID'] == 16).map({True: t_color, False: 'white'})
            pitch.scatter(df_dz['EVENT_X'], df_dz['EVENT_Y'], s=60, c=colors, edgecolors=t_color, ax=ax)
            draw_logo_adjusted(ax, t_logo)
            st.pyplot(fig)

    # --- TAB 3 & 4: ZONER ---
    def zone_tab(is_goal):
        c1, c2 = st.columns([1.8, 1])
        df_t = df_all[df_all['KLUB_NAVN'] == t_sel]
        plot_data = df_t[df_t['EVENT_TYPEID'] == 16] if is_goal else df_t
        z_counts = plot_data.groupby('Zone').size()
        
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            max_v = z_counts.max() if not z_counts.empty else 1
            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                cnt = z_counts.get(name, 0)
                alpha = (cnt/max_v) * 0.85 if cnt > 0 else 0.05
                ax.add_patch(patches.Rectangle(
                    (b["x_min"], max(b["y_min"], 55)), 
                    b["x_max"]-b["x_min"], 
                    b["y_max"]-max(b["y_min"], 55), 
                    facecolor=t_color, alpha=alpha, edgecolor='black', ls='--', lw=0.5
                ))
                if cnt > 0:
                    display_text_color = 'black' if alpha < 0.4 else txt_color
                    ax.text(
                        b["x_min"]+(b["x_max"]-b["x_min"])/2, 
                        max(b["y_min"], 55)+(b["y_max"]-max(b["y_min"], 55))/2, 
                        f"{cnt}", ha='center', va='center', fontsize=12, fontweight='bold', color=display_text_color
                    )
            draw_logo_adjusted(ax, t_logo)
            st.pyplot(fig)

    with tabs[3]: zone_tab(False)
    with tabs[4]: zone_tab(True)

if __name__ == "__main__":
    vis_side()
