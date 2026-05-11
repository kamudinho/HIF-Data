import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import base64
from data.utils.team_mapping import TEAMS
from data.data_load import _get_snowflake_conn

# --- 1. HJÆLPEFUNKTIONER ---

@st.cache_data(ttl=86400)
def get_base64_image(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            encoded_str = base64.b64encode(response.content).decode("utf-8")
            return f"data:image/png;base64,{encoded_str}"
    except: return url
    return url

@st.cache_data(ttl=3600)
def load_data():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    # A. Opta Matchinfo
    df_opta = conn.query(f"SELECT * FROM {db}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'")
    
    # B. Wyscout Performance
    df_wy = conn.query(f"""
        SELECT 
            tm.TEAM_WYID, 
            AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS,
            AVG(md.PPDA) as PPDA, AVG(mp.PASSES) as PASSES
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID
        WHERE tm.COMPETITION_WYID = 328 
        GROUP BY tm.TEAM_WYID
    """)
    
    # C. Second Spectrum (Fysisk - Union for hjemme/ude match)
    df_ss = conn.query(f"""
        WITH BASE AS (
            SELECT m.HOME_OPTAID as TEAM_ID, ps.DISTANCE, ps."HIGH SPEED RUNNING" as HSR
            FROM {db}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS ps
            JOIN {db}.SECONDSPECTRUM_GAME_METADATA m ON ps.MATCH_SSIID = m.MATCH_SSIID
            WHERE ps.MATCH_DATE >= '2025-07-01'
            UNION ALL
            SELECT m.AWAY_OPTAID as TEAM_ID, ps.DISTANCE, ps."HIGH SPEED RUNNING" as HSR
            FROM {db}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS ps
            JOIN {db}.SECONDSPECTRUM_GAME_METADATA m ON ps.MATCH_SSIID = m.MATCH_SSIID
            WHERE ps.MATCH_DATE >= '2025-07-01'
        )
        SELECT TEAM_ID, AVG(DISTANCE) / 1000 as DIST_KM, AVG(HSR) as HSR
        FROM BASE GROUP BY TEAM_ID
    """)
    
    return df_opta, df_wy, df_ss

def calculate_split_table(df_opta):
    """Beregner tabel med slutspils-logik (Top 6 / Bund 6 split efter runde 22)"""
    def get_points(df):
        stats = {}
        for _, row in df.iterrows():
            h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
            for uuid in [h_uuid, a_uuid]:
                if uuid not in stats: stats[uuid] = {'P': 0, 'MD': 0}
            h_g, a_g = int(row.get('TOTAL_HOME_SCORE', 0)), int(row.get('TOTAL_AWAY_SCORE', 0))
            stats[h_uuid]['MD'] += (h_g - a_g); stats[a_uuid]['MD'] += (a_g - h_g)
            if h_g > a_g: stats[h_uuid]['P'] += 3
            elif a_g > h_g: stats[a_uuid]['P'] += 3
            else: stats[h_uuid]['P'] += 1; stats[a_uuid]['P'] += 1
        return pd.DataFrame.from_dict(stats, orient='index').reset_index().rename(columns={'index': 'OPTA_UUID'})

    df_played = df_opta[df_opta['MATCH_STATUS'].str.contains('Played|Full|Finish', case=False, na=False)].sort_values('MATCH_DATE_FULL')
    
    # 1. Tabel efter runde 22 (for at finde de to grupper)
    # Vi antager at hver runde har 6 kampe
    df_r22 = df_played.head(22 * 6) 
    tabel_r22 = get_points(df_r22).sort_values(['P', 'MD'], ascending=False)
    top_6_uuids = tabel_r22.head(6)['OPTA_UUID'].tolist()
    
    # 2. Tabel nu (alle kampe)
    tabel_nu = get_points(df_played)
    
    # Del op og sorter hver for sig
    top_6_final = tabel_nu[tabel_nu['OPTA_UUID'].isin(top_6_uuids)].sort_values(['P', 'MD'], ascending=False)
    bund_6_final = tabel_nu[~tabel_nu['OPTA_UUID'].isin(top_6_uuids)].sort_values(['P', 'MD'], ascending=False)
    
    final_table = pd.concat([top_6_final, bund_6_final]).reset_index(drop=True)
    final_table['#'] = final_table.index + 1
    return final_table

# --- 2. CHART FUNKTION ---

def draw_position_performance_chart(df_merged, metric, label):
    if df_merged is None or df_merged.empty: return
    
    fig = go.Figure()
    df_merged[metric] = pd.to_numeric(df_merged[metric], errors='coerce')
    y_vals = df_merged[metric].dropna()
    if y_vals.empty: return
    
    y_span = y_vals.max() - y_vals.min() if y_vals.max() != y_vals.min() else 1
    is_ppda = "PPDA" in label.upper()

    # Tilføj en vertikal linje der markerer split mellem Top 6 og Bund 6
    fig.add_vline(x=6.5, line_width=2, line_dash="dash", line_color="gray", annotation_text="SPLIT")

    for _, row in df_merged.iterrows():
        if pd.notnull(row[metric]) and row.get('LOGO_URL'):
            b64_logo = get_base64_image(row['LOGO_URL'])
            fig.add_layout_image(dict(
                source=b64_logo, xref="x", yref="y",
                x=row['#'], y=row[metric],
                sizex=0.5, sizey=y_span * 0.35,
                xanchor="center", yanchor="bottom" if not is_ppda else "top"
            ))

    fig.add_trace(go.Scatter(
        x=df_merged['#'], y=df_merged[metric], mode='markers',
        marker=dict(size=45, opacity=0), hovertext=df_merged['HOLD_NAVN'],
        hovertemplate="<b>%{hovertext}</b><br>Placering: %{x}<br>"+label+": %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        height=600, margin=dict(t=30, b=60, l=60, r=40),
        xaxis=dict(title="<b>Slutspilsplacering</b>", tickmode='linear', range=[0.4, 12.6], gridcolor="#f0f0f0"),
        yaxis=dict(title=f"<b>{label}</b>", gridcolor="#f0f0f0", autorange="reversed" if is_ppda else True),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig, use_container_width=True)

# --- 3. VIS SIDE ---

def vis_side():
    df_opta, df_wy, df_ss = load_data()
    if df_opta is None or df_opta.empty: return

    df_opta.columns = [c.upper() for c in df_opta.columns]
    df_liga = calculate_split_table(df_opta)

    final_data = []
    for _, row in df_liga.iterrows():
        opt_uuid = row['OPTA_UUID']
        team_info = next((info for name, info in TEAMS.items() if info.get('opta_uuid') == opt_uuid), None)
        team_name = next((name for name, info in TEAMS.items() if info.get('opta_uuid') == opt_uuid), "Ukendt")
        
        if team_info:
            perf = df_wy[df_wy['TEAM_WYID'] == team_info.get('team_wyid')]
            try:
                m_id = str(team_info.get('opta_id'))
                fysisk = df_ss[df_ss['TEAM_ID'].astype(str) == m_id]
            except: fysisk = pd.DataFrame()
            
            final_data.append({
                '#': row['#'], 'HOLD_NAVN': team_name, 'LOGO_URL': team_info.get('logo'),
                'XG': perf['XG'].iloc[0] if not perf.empty else np.nan,
                'SHOTS': perf['SHOTS'].iloc[0] if not perf.empty else np.nan,
                'GOALS': perf['GOALS'].iloc[0] if not perf.empty else np.nan,
                'PASSES': perf['PASSES'].iloc[0] if not perf.empty else np.nan,
                'PPDA': perf['PPDA'].iloc[0] if not perf.empty else np.nan,
                'DIST': fysisk['DIST_KM'].iloc[0] if not fysisk.empty else np.nan,
                'HSR': fysisk['HSR'].iloc[0] if not fysisk.empty else np.nan
            })

    df_final = pd.DataFrame(final_data)

    col1, col2 = st.columns([2.5, 1.5])
    with col1:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("NordicBet Liga: Slutspils-placering vs. Performance")
    with col2:
        metric_map = {
            "xG (Wyscout)": "XG", "Mål": "GOALS", "Skud": "SHOTS", 
            "Afleveringer": "PASSES", "Pres (PPDA)": "PPDA", 
            "Distance (km) (SS)": "DIST", "High Speed Running (m) (SS)": "HSR"
        }
        sel_metric = st.selectbox("", list(metric_map.keys()), label_visibility="collapsed")
    
    draw_position_performance_chart(df_final, metric_map[sel_metric], sel_metric)

if __name__ == "__main__":
    vis_side()
