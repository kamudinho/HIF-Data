import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import base64

# --- IMPORT DYNAMISKE KONSTANTER OG MAPPINGS ---
from data.utils.team_mapping import (
    SEASONS,
    COMPETITIONS,
    SEASON_LEAGUE_MAPPER,
    TEAMS,
    COMPETITION_NAME as DEFAULT_COMP,
    TOURNAMENTCALENDAR_NAME as DEFAULT_SEASON
)
from data.data_load import _get_snowflake_conn

# --- 1. HJÆLPEFUNKTIONER ---

@st.cache_data(ttl=86400)
def get_base64_image(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            encoded_str = base64.b64encode(response.content).decode("utf-8")
            return f"data:image/png;base64,{encoded_str}"
    except: 
        return url
    return url

@st.cache_data(ttl=3600)
def load_data(periode, start, split, slut, calendar_uuid, wyid):
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    if "Efterår" in periode:
        filter_sql = f"BETWEEN '{start}' AND '{split}'"
    elif "Forår" in periode:
        filter_sql = f"BETWEEN '{pd.to_datetime(split) + pd.Timedelta(days=1)}' AND '{slut}'"
    else:
        filter_sql = f"BETWEEN '{start}' AND '{slut}'"

    df_opta = pd.DataFrame()
    if calendar_uuid:
        df_opta = conn.query(f"""
            SELECT * FROM {db}.OPTA_MATCHINFO 
            WHERE TOURNAMENTCALENDAR_OPTAUUID = '{calendar_uuid}'
            AND MATCH_DATE_FULL {filter_sql}
        """)
    
    df_wy = pd.DataFrame()
    if wyid:
        df_wy = conn.query(f"""
            SELECT 
                tm.TEAM_WYID, 
                AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS,
                AVG(md.PPDA) as PPDA, AVG(mp.PASSES) as PASSES
            FROM {db}.WYSCOUT_TEAMMATCHES tm 
            LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
            LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
            LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID
            WHERE tm.COMPETITION_WYID = {wyid} 
            AND tm.DATE {filter_sql} 
            GROUP BY tm.TEAM_WYID
        """)
    
    df_ss = conn.query(f"""
        WITH BASE AS (
            SELECT m.HOME_OPTAID as TEAM_ID, ps.DISTANCE, ps."HIGH SPEED RUNNING" as HSR
            FROM {db}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS ps
            JOIN {db}.SECONDSPECTRUM_GAME_METADATA m ON ps.MATCH_SSIID = m.MATCH_SSIID
            WHERE ps.MATCH_DATE {filter_sql}
            UNION ALL
            SELECT m.AWAY_OPTAID as TEAM_ID, ps.DISTANCE, ps."HIGH SPEED RUNNING" as HSR
            FROM {db}.SECONDSPECTRUM_PHYSICAL_SUMMARY_PLAYERS ps
            JOIN {db}.SECONDSPECTRUM_GAME_METADATA m ON ps.MATCH_SSIID = m.MATCH_SSIID
            WHERE ps.MATCH_DATE {filter_sql}
        )
        SELECT TEAM_ID, AVG(DISTANCE) / 1000 as DIST_KM, AVG(HSR) as HSR
        FROM BASE GROUP BY TEAM_ID
    """)
    
    return df_opta, df_wy, df_ss

def calculate_split_table(df_opta, valgt_saeson, valgt_turnering):
    def get_points(df):
        stats = {}
        forventede_hold = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(valgt_turnering, [])
        for h_navn in forventede_hold:
            info = TEAMS.get(h_navn, {})
            u_id = info.get('opta_uuid', h_navn)
            stats[u_id] = {'P': 0, 'MD': 0}

        if df is not None and not df.empty:
            for _, row in df.iterrows():
                h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
                for uuid in [h_uuid, a_uuid]:
                    if uuid not in stats: stats[uuid] = {'P': 0, 'MD': 0}
                h_g, a_g = int(row.get('TOTAL_HOME_SCORE', 0) or 0), int(row.get('TOTAL_AWAY_SCORE', 0) or 0)
                stats[h_uuid]['MD'] += (h_g - a_g); stats[a_uuid]['MD'] += (a_g - h_g)
                if h_g > a_g: stats[h_uuid]['P'] += 3
                elif a_g > h_g: stats[a_uuid]['P'] += 3
                else: stats[h_uuid]['P'] += 1; stats[a_uuid]['P'] += 1
                
        return pd.DataFrame.from_dict(stats, orient='index').reset_index().rename(columns={'index': 'OPTA_UUID'})

    df_played = pd.DataFrame()
    if df_opta is not None and not df_opta.empty and 'MATCH_STATUS' in df_opta.columns:
        df_played = df_opta[df_opta['MATCH_STATUS'].str.contains('Played|Full|Finish', case=False, na=False)].sort_values('MATCH_DATE_FULL')
    
    df_r22 = df_played.head(132) if not df_played.empty else df_played
    tabel_r22 = get_points(df_r22).sort_values(['P', 'MD'], ascending=False)
    top_6_uuids = tabel_r22.head(6)['OPTA_UUID'].tolist()
    
    tabel_nu = get_points(df_played)
    
    top_6_final = tabel_nu[tabel_nu['OPTA_UUID'].isin(top_6_uuids)].sort_values(['P', 'MD'], ascending=False)
    bund_6_final = tabel_nu[~tabel_nu['OPTA_UUID'].isin(top_6_uuids)].sort_values(['P', 'MD'], ascending=False)
    
    final_table = pd.concat([top_6_final, bund_6_final]).reset_index(drop=True)
    final_table['#'] = final_table.index + 1
    return final_table

# --- 2. CHART FUNKTION ---

def draw_position_performance_chart(df_merged, metric, label, periode_tekst):
    if df_merged is None or df_merged.empty:
        st.warning("Ingen data tilgængelig.")
        return

    fig = go.Figure()
    df_merged[metric] = pd.to_numeric(df_merged[metric], errors='coerce')
    
    # Tjek om vi har rigtige data, eller om der slet ingen data er endnu
    y_vals = df_merged[metric].dropna()
    has_data = not y_vals.empty

    if has_data:
        y_min = y_vals.min()
        y_max = y_vals.max()
        y_span = y_max - y_min if y_max != y_min else 1.0
        y_range = None
    else:
        # Ingen data endnu: sæt alle y-værdier til 0.0 så de står på en lige linje
        df_merged[metric] = 0.0
        y_span = 1.0
        y_range = [-0.5, 0.5]  # Fast låst akse så linjen placerer sig pænt i midten

    is_reversed = "PPDA" in label.upper() or "IMOD" in label.upper()

    for _, row in df_merged.iterrows():
        if pd.notnull(row[metric]) and row.get('LOGO_URL'):
            b64_logo = get_base64_image(row['LOGO_URL'])
            fig.add_layout_image(dict(
                source=b64_logo, xref="x", yref="y",
                x=row['#'], y=row[metric],
                sizex=0.5, 
                sizey=y_span * 0.35 if has_data else 0.3,
                xanchor="center", 
                yanchor="middle" if not has_data else ("top" if is_reversed else "bottom")
            ))

    # Scatter trace til hover-effekt og positionering
    fig.add_trace(go.Scatter(
        x=df_merged['#'], y=df_merged[metric], mode='markers',
        marker=dict(size=45, opacity=0), 
        hovertext=df_merged['HOLD_NAVN'],
        hovertemplate="<b>%{hovertext}</b><br>Placering: %{x}<br>" + 
                      (f"{label}: %{{y:.2f}}" if has_data else "Ingen data endnu") + "<extra></extra>"
    ))

    # Konfigurer Y-akse med hensyntagen til om der er data eller ej
    yaxis_config = dict(
        title=f"<b>{label}</b>", 
        gridcolor="#f0f0f0", 
        linecolor='black'
    )
    if has_data:
        yaxis_config['autorange'] = "reversed" if is_reversed else True
    else:
        yaxis_config['range'] = y_range
        yaxis_config['showticklabels'] = False  # Skjul y-værdierne (f.eks. 0.0) når der ikke er data

    fig.update_layout(
        height=600, margin=dict(t=50, b=60, l=60, r=40),
        xaxis=dict(title="<b>Placering</b>", tickmode='linear', range=[0.4, 12.6], gridcolor="#f0f0f0", linecolor='black'),
        yaxis=yaxis_config,
        plot_bgcolor='white',
        annotations=[dict(
            x=1, y=1.04, xref='paper', yref='paper',
            text=f"<b>{periode_tekst}</b>",
            showarrow=False, font=dict(size=13, color="#666666"),
            xanchor='right'
        )]
    )
    st.plotly_chart(fig, use_container_width=True)

# --- 3. HOVEDFUNKTION ---

def vis_side():
    y_start = DEFAULT_SEASON.split('/')[0] if '/' in DEFAULT_SEASON else "2025"
    y_end = f"20{DEFAULT_SEASON.split('/')[1]}" if '/' in DEFAULT_SEASON else "2026"

    start_dato = f"{y_start}-07-01"
    split_dato = f"{y_start}-12-31" 
    slut_dato = f"{y_end}-06-30"

    calendar_uuid = SEASONS.get(DEFAULT_SEASON, {}).get(DEFAULT_COMP)
    wyid = COMPETITIONS.get(DEFAULT_COMP, {}).get("wyid", 328)

    col_title, col_m, col_p = st.columns([2.0, 1.0, 1.0])
    
    with col_m:
        metric_map = {
            "xG": "XG", "Mål": "GOALS", "Mål imod": "GOALS_AGAINST", "Skud": "SHOTS", 
            "Afleveringer": "PASSES", "PPDA": "PPDA", 
            "Distance": "DIST", "High Speed Running": "HSR"
        }
        sel_metric = st.selectbox("Parameter:", list(metric_map.keys()))

    with col_p:
        opt_efteraar = f"Efterår {y_start}"
        opt_foraar = f"Forår {y_end}"
        opt_hele = f"{DEFAULT_SEASON}"
        
        periode = st.selectbox("Periode:", [opt_hele, opt_efteraar, opt_foraar])

    if periode == opt_efteraar:
        tekst_beskrivelse = opt_efteraar
    elif periode == opt_foraar:
        tekst_beskrivelse = opt_foraar
    else:
        tekst_beskrivelse = f"Samlet for sæson {DEFAULT_SEASON}"

    with col_title:
        st.subheader(DEFAULT_COMP)
        st.caption("Placering vs. Performance")

    df_opta, df_wy, df_ss = load_data(periode, start_dato, split_dato, slut_dato, calendar_uuid, wyid)
    
    if df_opta is not None and not df_opta.empty:
        df_opta.columns = [c.upper() for c in df_opta.columns]

    df_liga = calculate_split_table(df_opta, DEFAULT_SEASON, DEFAULT_COMP)
    
    final_data = []
    for _, row in df_liga.iterrows():
        opt_uuid = row['OPTA_UUID']
        
        team_info = next((info for name, info in TEAMS.items() if info.get('opta_uuid') == opt_uuid), None)
        team_name = next((name for name, info in TEAMS.items() if info.get('opta_uuid') == opt_uuid), "Ukendt")
        
        if team_info:
            perf = df_wy[df_wy['TEAM_WYID'] == team_info.get('team_wyid')] if df_wy is not None and not df_wy.empty else pd.DataFrame()
            
            try:
                m_id = str(team_info.get('opta_id'))
                fysisk = df_ss[df_ss['TEAM_ID'].astype(str) == m_id] if df_ss is not None and not df_ss.empty else pd.DataFrame()
            except:
                fysisk = pd.DataFrame()
            
            final_data.append({
                '#': row['#'],
                'HOLD_NAVN': team_name,
                'LOGO_URL': team_info.get('logo'),
                'XG': perf['XG'].iloc[0] if not perf.empty and 'XG' in perf.columns else np.nan,
                'SHOTS': perf['SHOTS'].iloc[0] if not perf.empty and 'SHOTS' in perf.columns else np.nan,
                'GOALS': perf['GOALS'].iloc[0] if not perf.empty and 'GOALS' in perf.columns else np.nan,
                'PASSES': perf['PASSES'].iloc[0] if not perf.empty and 'PASSES' in perf.columns else np.nan,
                'PPDA': perf['PPDA'].iloc[0] if not perf.empty and 'PPDA' in perf.columns else np.nan,
                'DIST': fysisk['DIST_KM'].iloc[0] if not fysisk.empty and 'DIST_KM' in fysisk.columns else np.nan,
                'HSR': fysisk['HSR'].iloc[0] if not fysisk.empty and 'HSR' in fysisk.columns else np.nan
            })

    df_final = pd.DataFrame(final_data)
    
    draw_position_performance_chart(df_final, metric_map[sel_metric], sel_metric, tekst_beskrivelse)

if __name__ == "__main__":
    vis_side()
