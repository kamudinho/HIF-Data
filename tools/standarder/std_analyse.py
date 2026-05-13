import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- KONFIGURATION ---
HIF_RED = '#cc0000'
DB = "KLUB_HVIDOVREIF.AXIS"
LIGA_UUID = "dyjr458hcmrcy87fsabfsy87o" 
PLAYER_FILE = 'data/players/1div_overskrivning.csv'

@st.cache_data(ttl=3600)
def load_setpiece_data():
    conn = _get_snowflake_conn()
    if not conn: return pd.DataFrame()
    
    sql = f"""
    WITH BaseEvents AS (
        SELECT 
            e.EVENT_OPTAUUID, e.MATCH_OPTAUUID, e.EVENT_EVENTID,
            e.EVENT_CONTESTANT_OPTAUUID AS TEAM_UUID,
            e.EVENT_TYPEID,
            TRIM(e.PLAYER_OPTAUUID) AS PLAYER_UUID,
            e.PLAYER_NAME,
            e.EVENT_X, e.EVENT_Y,
            LEAD(TRIM(e.PLAYER_OPTAUUID), 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_UUID,
            LEAD(e.PLAYER_NAME, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_NAME,
            LEAD(e.EVENT_CONTESTANT_OPTAUUID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_TEAM,
            LEAD(e.EVENT_TYPEID, 1) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P1_TYPE,
            LEAD(e.EVENT_TYPEID, 2) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P2_TYPE,
            LEAD(e.EVENT_TYPEID, 3) OVER (PARTITION BY e.MATCH_OPTAUUID ORDER BY e.EVENT_EVENTID) AS P3_TYPE
        FROM {DB}.OPTA_EVENTS e
        WHERE e.TOURNAMENTCALENDAR_OPTAUUID = '{LIGA_UUID}'
    ),
    Quals AS (
        SELECT 
            EVENT_OPTAUUID,
            MAX(CASE WHEN QUALIFIER_QID = 107 THEN 'Indkast'
                     WHEN QUALIFIER_QID = 6 THEN 'Hjørnespark'
                     WHEN QUALIFIER_QID = 5 THEN 'Frispark' END) AS TYPE_NAVN,
            MAX(CASE WHEN QUALIFIER_QID = 140 THEN QUALIFIER_VALUE END) AS ENDX,
            MAX(CASE WHEN QUALIFIER_QID = 141 THEN QUALIFIER_VALUE END) AS ENDY
        FROM {DB}.OPTA_QUALIFIERS
        WHERE QUALIFIER_QID IN (5, 6, 107, 140, 141)
        GROUP BY EVENT_OPTAUUID
    )
    SELECT b.*, q.TYPE_NAVN, q.ENDX, q.ENDY
    FROM BaseEvents b
    JOIN Quals q ON b.EVENT_OPTAUUID = q.EVENT_OPTAUUID
    WHERE q.TYPE_NAVN IS NOT NULL
    """
    try:
        df = conn.query(sql)
        if df is None or df.empty: return pd.DataFrame()
        df.columns = [c.upper() for c in df.columns]
        
        try:
            df_lookup = pd.read_csv(PLAYER_FILE)
            df_lookup['PLAYER_OPTAUUID'] = df_lookup['PLAYER_OPTAUUID'].astype(str).str.strip()
            name_map = df_lookup.set_index('PLAYER_OPTAUUID')['NAVN'].to_dict()
        except:
            name_map = {}

        df['TAGER_NAVN'] = df.apply(lambda x: name_map.get(str(x['PLAYER_UUID']).strip(), x['PLAYER_NAME']), axis=1)
        
        def find_target(row):
            if row['P1_TEAM'] == row['TEAM_UUID'] and row['P1_UUID'] != row['PLAYER_UUID']:
                return name_map.get(str(row['P1_UUID']).strip(), row['P1_NAME'])
            return None
        df['MODTAGER'] = df.apply(find_target, axis=1)

        shot_types = [13, 14, 15, 16]
        df['ER_AFSLUTNING'] = df.apply(lambda x: 1 if x['P1_TYPE'] in shot_types or x['P2_TYPE'] in shot_types or x['P3_TYPE'] in shot_types else 0, axis=1)
        
        return df
    except:
        return pd.DataFrame()

def to_metric(val, total_m): 
    return val * (total_m / 100)

def get_summary_stats(df, group_col):
    if df.empty: return pd.DataFrame()
    
    # Basis stats
    stats = df.groupby(group_col).agg(
        Antal=('TYPE_NAVN', 'size'),
        Succesfulde=('MODTAGER', lambda x: x.notna().sum()),
        Afslutninger=('ER_AFSLUTNING', 'sum')
    ).reset_index()
    
    stats['Succes %'] = (stats['Succesfulde'] / stats['Antal']).fillna(0)
    stats['Afslutning %'] = (stats['Afslutninger'] / stats['Antal']).fillna(0)
    
    # Top modtager (Generelt)
    def get_top_mod(sub_df):
        m = sub_df['MODTAGER'].value_counts()
        return f"{m.index[0]} ({m.iloc[0]})" if not m.empty else "-"
    
    # Top modtager (Kun ved afslutning)
    def get_top_mod_shot(sub_df):
        m = sub_df[sub_df['ER_AFSLUTNING'] == 1]['MODTAGER'].value_counts()
        return f"{m.index[0]} ({m.iloc[0]})" if not m.empty else "-"

    stats['Top Modtager'] = stats[group_col].map(df.groupby(group_col).apply(get_top_mod).to_dict())
    stats['Top Modtager (Afsl.)'] = stats[group_col].map(df.groupby(group_col).apply(get_top_mod_shot).to_dict())
    
    # Sorter kolonnerne efter ønsket rækkefølge
    final_cols = [group_col, 'Antal', 'Succesfulde', 'Succes %', 'Top Modtager', 'Afslutninger', 'Afslutning %', 'Top Modtager (Afsl.)']
    return stats[final_cols]

def render_setpiece_analysis(df_team, sp_type, t_sel):
    f1, f2 = st.columns([1, 1])
    with f1:
        p_list = ["Alle spillere"] + sorted(df_team[df_team['TYPE_NAVN'] == sp_type]['TAGER_NAVN'].unique().tolist())
        p_sel = st.selectbox(f"Spiller ({sp_type})", p_list, key=f"sb_p_{sp_type}")
    with f2:
        vis_mode = st.selectbox(f"Visning ({sp_type})", ["Zoner + Pile", "Kun Zoner", "Kun Pile"], key=f"sb_m_{sp_type}")

    mask = (df_team['TYPE_NAVN'] == sp_type)
    if p_sel != "Alle spillere": mask &= (df_team['TAGER_NAVN'] == p_sel)
    df_plot = df_team[mask].copy()

    col_p, col_s = st.columns([2, 1])
    with col_p:
        for c in ['EVENT_X', 'EVENT_Y', 'ENDX', 'ENDY']: 
            df_plot[c] = pd.to_numeric(df_plot[c], errors='coerce')
        df_plot['X_M'] = df_plot['EVENT_X'].apply(lambda x: to_metric(x, 105))
        df_plot['Y_M'] = df_plot['EVENT_Y'].apply(lambda y: to_metric(y, 68))
        df_plot['ENDX_M'] = df_plot['ENDX'].apply(lambda x: to_metric(x, 105))
        df_plot['ENDY_M'] = df_plot['ENDY'].apply(lambda y: to_metric(y, 68))
        pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='#cccccc')
        fig, ax = pitch.draw(figsize=(10, 10))
        ax.set_ylim(50, 105)
        if not df_plot.dropna(subset=['ENDX_M', 'ENDY_M']).empty:
            if "Zoner" in vis_mode:
                pitch.hexbin(df_plot.ENDX_M, df_plot.ENDY_M, ax=ax, gridsize=(12, 12), cmap='Reds', alpha=0.6)
            if "Pile" in vis_mode:
                pitch.arrows(df_plot.X_M, df_plot.Y_M, df_plot.ENDX_M, df_plot.ENDY_M, 
                             color=TEAM_COLORS.get(t_sel, {}).get('primary', HIF_RED), ax=ax, alpha=0.3)
        st.pyplot(fig)
    with col_s:
        m1, m2, m3 = st.columns(3)
        m1.metric("Antal", len(df_plot))
        m2.metric("Succes", df_plot['MODTAGER'].notna().sum())
        m3.metric("Afslutn.", df_plot['ER_AFSLUTNING'].sum())
        st.write("---") 
        st.write("**Top modtagere**")
        mod_counts = df_plot['MODTAGER'].value_counts().reset_index()
        mod_counts.columns = ['Spiller', 'Antal']
        st.dataframe(mod_counts, use_container_width=True, hide_index=True)

def vis_side():
    st.set_page_config(layout="wide", page_title="Standardsituationer")
    
    st.markdown("""
        <style>
        header {visibility: hidden;}
        div[data-testid="stSelectbox"] label { display: none !important; }
        div[data-testid="stHorizontalBlock"] { align-items: center; }
        </style>
    """, unsafe_allow_html=True)
    
    df_all = load_setpiece_data()
    if df_all.empty:
        st.warning("Ingen data fundet.")
        return

    uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
    df_all['KLUB_NAVN'] = df_all['TEAM_UUID'].str.upper().map(uuid_to_name)
    teams = sorted([n for n in df_all['KLUB_NAVN'].unique() if pd.notna(n)])

    col_title, col_empty, col_select = st.columns([2, 1, 1])
    with col_title:
        st.subheader("Standardsituationer")
    with col_select:
        t_sel = st.selectbox("hold_valg_top", teams, index=teams.index("Hvidovre") if "Hvidovre" in teams else 0)

    df_team_selected = df_all[df_all['KLUB_NAVN'] == t_sel].copy()

    tabs = st.tabs(["Holdoversigt", "Spilleroversigt", "Hjørnespark", "Frispark", "Indkast", "Zoneoversigt"])
    cat_options = ["Hjørnespark", "Frispark", "Indkast"]

    # Opdateret kolonne-rækkefølge og navne
    col_cfg = {
        "KLUB_NAVN": "Klub",
        "TAGER_NAVN": "Spiller",
        "Succes %": st.column_config.ProgressColumn("Succes %", format="%.0f%%", min_value=0, max_value=1),
        "Top Modtager": "Top Modtager (Succes)",
        "Afslutning %": st.column_config.ProgressColumn("Afslutning %", format="%.0f%%", min_value=0, max_value=1),
        "Top Modtager (Afsl.)": "Top Modtager (Afsl.)"
    }

    with tabs[0]: 
        c_label, c_radio = st.columns([0.15, 0.85])
        with c_label: st.write("**Kategori**")
        with c_radio: cat_h = st.radio("cat_h", cat_options, horizontal=True, label_visibility="collapsed", key="radio_hold")
        
        stats_h = get_summary_stats(df_all[df_all['TYPE_NAVN'] == cat_h], 'KLUB_NAVN')
        st.dataframe(stats_h, use_container_width=True, hide_index=True, height=500, column_config=col_cfg)

    with tabs[1]: 
        c_label_s, c_radio_s = st.columns([0.15, 0.85])
        with c_label_s: st.write("**Kategori**")
        with c_radio_s: cat_s = st.radio("cat_s", cat_options, horizontal=True, label_visibility="collapsed", key="radio_spiller")
        
        df_cat_s = df_team_selected[df_team_selected['TYPE_NAVN'] == cat_s]
        if not df_cat_s.empty:
            stats_s = get_summary_stats(df_cat_s, 'TAGER_NAVN')
            st.dataframe(stats_s, use_container_width=True, hide_index=True, height=500, column_config=col_cfg)

    with tabs[2]: render_setpiece_analysis(df_team_selected, "Hjørnespark", t_sel)
    with tabs[3]: render_setpiece_analysis(df_team_selected, "Frispark", t_sel)
    with tabs[4]: render_setpiece_analysis(df_team_selected, "Indkast", t_sel)

    with tabs[5]:
        df_team_selected['ZONE'] = df_team_selected['ENDY'].apply(lambda y: "Venstre" if float(y or 0) < 33 else ("Højre" if float(y or 0) > 66 else "Center"))
        zone_stats = df_team_selected.groupby(['ZONE', 'TYPE_NAVN']).size().unstack(fill_value=0).reset_index()
        st.dataframe(zone_stats, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    vis_side()
