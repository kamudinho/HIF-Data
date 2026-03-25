import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn
from PIL import Image
import requests
from io import BytesIO

# --- KONFIGURATION ---
HIF_RED = '#cc0000'
HIF_GOLD = '#FFD700'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o"

# --- DATA LOAD ---
@st.cache_data(ttl=3600)
def load_league_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    match_sql = f"SELECT DISTINCT MATCH_OPTAUUID FROM {DB}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'"
    sql = f"""
        SELECT e.*, q.QUALIFIER_VALUE as XG_RAW FROM {DB}.OPTA_EVENTS e 
        LEFT JOIN {DB}.OPTA_QUALIFIERS q ON e.EVENT_OPTAUUID = q.EVENT_OPTAUUID AND q.QUALIFIER_QID = 321
        WHERE e.EVENT_TYPEID IN (13,14,15,16) AND e.MATCH_OPTAUUID IN ({match_sql})
    """
    df = conn.query(sql) if hasattr(conn, 'query') else pd.read_sql(sql, conn)
    df.columns = [c.upper() for c in df.columns]
    return df

@st.cache_data(ttl=3600)
def get_logo_img(url):
    try: return Image.open(BytesIO(requests.get(url, timeout=5).content))
    except: return None

# --- MAIN APP ---
def vis_side(dp=None):
    df_all = load_league_data()
    if df_all.empty: return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['EVENT_CONTESTANT_OPTAUUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    t_sel = st.selectbox("Vælg hold", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)
    t_color = TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED)
    t_logo = get_logo_img(TEAMS.get(t_sel, {}).get('logo'))
    
    df_team = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    tabs = st.tabs(["AFSLUTNINGER", "DZ-ANALYSE"])

    with tabs[0]:
        c1, c2 = st.columns([2, 1])
        with c2:
            p_sel = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_team['PLAYER_NAME'].unique()))
            d_v = df_team if p_sel == "Hele Holdet" else df_team[df_team['PLAYER_NAME'] == p_sel]
            st.metric("Skud", len(d_v))
            st.metric("Mål", len(d_v[d_v['EVENT_TYPEID']==16]))
        with c1:
            # Den oprindelige pitch-opsætning med meget plads i bunden
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, 
                          c=(d_v['EVENT_TYPEID']==16).map({True: t_color, False: 'white'}), 
                          edgecolors=t_color, ax=ax)
            if t_logo:
                ax_logo = ax.inset_axes([0.05, 0.85, 0.15, 0.15])
                ax_logo.imshow(t_logo)
                ax_logo.axis('off')
            st.pyplot(fig)

    with tabs[1]:
        # Logik for DZ-analyse i den oprindelige version...
        st.write("DZ-Analyse indhold")

if __name__ == "__main__":
    vis_side()
