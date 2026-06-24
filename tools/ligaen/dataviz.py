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
def load_data(periode, start, split, slut):
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    if periode == "Efterår 2025":
        filter_sql = f"BETWEEN '{start}' AND '{split}'"
    elif periode == "Forår 2026":
        filter_sql = f"BETWEEN '{pd.to_datetime(split) + pd.Timedelta(days=1)}' AND '{slut}'"
    else:
        filter_sql = f"BETWEEN '{start}' AND '{slut}'"

    # A. Opta Matchinfo
    df_opta = conn.query(f"""
        SELECT * FROM {db}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'
        AND MATCH_DATE_FULL {filter_sql}
    """)
    
    # B. Wyscout Performance (Sikret mod DATE_UTC / DATE efter behov)
    df_wy = conn.query(f"""
        SELECT 
            tm.TEAM_WYID, 
            AVG(adv.XG) as XG, AVG(adv.GOALSCONCEDED) as GOALS_AGAINST, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS,
            AVG(md.PPDA) as PPDA, AVG(mp.PASSES) as PASSES
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID
        WHERE tm.COMPETITION_WYID = 328 
        AND tm.DATE {filter_sql} 
        GROUP BY tm.TEAM_WYID
    """)
    
    # C. Second Spectrum
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
    
def calculate_split_table(df_opta):
    """Beregner tabel med Top 6 / Bund 6 split baseret på runde 22-reglen"""
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
    
    df_r22 = df_played.head(132) 
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
    y_vals = df_merged[metric].dropna()
    if y_vals.empty: return
    
    y_min, y_max = y_vals.min(), y_vals.max()
    y_span = y_max - y_min if y_max != y_min else 1
    is_ppda = "PPDA" in label.upper()

    for _, row in df_merged.iterrows():
        if pd.notnull(row[metric]) and row.get('LOGO_URL'):
            b64_logo = get_base64_image(row['LOGO_URL'])
            fig.add_layout_image(dict(
                source=b64_logo, xref="x", yref="y",
                x=row['#'], y=row[metric],
                sizex=0.5, 
                sizey=y_span * 0.35,
                xanchor="center", 
                yanchor="bottom" if not is_ppda else "top"
            ))

    fig.add_trace(go.Scatter(
        x=df_merged['#'], y=df_merged[metric], mode='markers',
        marker=dict(size=45, opacity=0), 
        hovertext=df_merged['HOLD_NAVN'],
        hovertemplate="<b>%{hovertext}</b><br>Placering: %{x}<br>"+label+": %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        height=600, margin=dict(t=50, b=60, l=60, r=40),
        xaxis=dict(title="<b>Placering</b>", tickmode='linear', range=[0.4, 12.6], gridcolor="#f0f0f0", linecolor='black'),
        yaxis=dict(title=f"<b>{label}</b>", gridcolor="#f0f0f0", autorange="reversed" if is_ppda else True, linecolor='black'),
        plot_bgcolor='white',
        # Tekst i øverste højre hjørne af selve grafområdet
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
    start_dato = "2025-07-01"
    split_dato = "2025-12-31" 
    slut_dato = "2026-06-30"

    # --- TOP MENU MED DROPDOWNS TIL HØJRE ---
    col_title, col_m, col_p = st.columns([2.0, 1.0, 1.0])
    
    with col_m:
        metric_map = {
            "xG": "XG", "Mål": "GOALS", "Mål imod": "GOALS_AGAINST", "Skud": "SHOTS", 
            "Afleveringer": "PASSES", "PPDA": "PPDA", 
            "Distance": "DIST", "High Speed Running": "HSR"
        }
        sel_metric = st.selectbox("Parameter:", list(metric_map.keys()))

    with col_p:
        periode = st.selectbox("Periode:", ["2025/2026", "EFterår 2025", "Forår 2026"])

    # Generer den tekst-streng der skal indlejres i grafen
    if periode == "Efterår 2025":
        tekst_beskrivelse = "Efterår 2025"
    elif periode == "Forår 2026":
        tekst_beskrivelse = "Forår 2026"
    else:
        tekst_beskrivelse = "Samlet for sæson 2025/2026"

    with col_title:
        st.subheader("Betinia Ligaen")
        st.caption("Placering vs. Performance")

    # Data load og filtrering
    df_opta, df_wy, df_ss = load_data(periode, start_dato, split_dato, slut_dato)
    if df_opta is None or df_opta.empty: 
        st.info("Ingen data fundet for den valgte periode.")
        return

    df_opta.columns = [c.upper() for c in df_opta.columns]
    df_liga = calculate_split_table(df_opta)
    
    # Opbygning af det endelige performance data-grundlag
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
            except:
                fysisk = pd.DataFrame()
            
            final_data.append({
                '#': row['#'],
                'HOLD_NAVN': team_name,
                'LOGO_URL': team_info.get('logo'),
                'XG': perf['XG'].iloc[0] if not perf.empty else np.nan,
                'SHOTS': perf['SHOTS'].iloc[0] if not perf.empty else np.nan,
                'GOALS': perf['GOALS'].iloc[0] if not perf.empty else np.nan,
                'GOALS AGAINST': perf['GOALS_AGAINST'].iloc[0] if not perf.empty else np.nan,
                'PASSES': perf['PASSES'].iloc[0] if not perf.empty else np.nan,
                'PPDA': perf['PPDA'].iloc[0] if not perf.empty else np.nan,
                'DIST': fysisk['DIST_KM'].iloc[0] if not fysisk.empty else np.nan,
                'HSR': fysisk['HSR'].iloc[0] if not fysisk.empty else np.nan
            })

    df_final = pd.DataFrame(final_data)
    
    # Her kaldes grafen korrekt efter dataen er bygget færdig
    draw_position_performance_chart(df_final, metric_map[sel_metric], sel_metric, tekst_beskrivelse)

if __name__ == "__main__":
    vis_side()
