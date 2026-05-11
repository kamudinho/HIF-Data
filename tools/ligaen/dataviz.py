import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import base64
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. HJÆLPEFUNKTIONER ---

@st.cache_data(ttl=86400)
def get_base64_image(url):
    """Konverterer URL til Base64 så logoer kan eksporteres i PNG."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            encoded_str = base64.b64encode(response.content).decode("utf-8")
            return f"data:image/png;base64,{encoded_str}"
    except Exception:
        return url
    return url

@st.cache_data(ttl=3600)
def load_data():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    
    # Opta Data - Tabelgrundlag
    df_opta = conn.query(f"SELECT * FROM {db}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'")
    
    # Wyscout Data - Performance grundlag
    df_wy = conn.query(f"""
        SELECT t.TEAMNAME, t.TEAM_WYID,
               AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, 
               AVG(md.PPDA) as PPDA, AVG(mp.PASSES) as PASSES
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        JOIN {db}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        JOIN {db}.WYSCOUT_SEASONS s ON tm.SEASON_WYID = s.SEASON_WYID
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328 AND s.SEASONNAME = '2025/2026'
        GROUP BY t.TEAMNAME, t.TEAM_WYID
    """)
    return df_opta, df_wy

# --- 2. CHART FUNKTION ---

def draw_position_performance_chart(df_merged, metric, label):
    if df_merged is None or df_merged.empty:
        st.warning("Ingen data tilgængelig.")
        return

    fig = go.Figure()

    # Type-cast til float for at undgå Decimal-fejl
    df_merged[metric] = df_merged[metric].apply(lambda x: float(x) if x is not None else np.nan)
    
    y_vals = df_merged[metric].dropna()
    if y_vals.empty: return
    
    y_min, y_max = y_vals.min(), y_vals.max()
    y_span = y_max - y_min if y_max != y_min else 1
    
    is_ppda = "PPDA" in label.upper()

    for _, row in df_merged.iterrows():
        logo_url = row.get('LOGO_URL', "")
        
        if logo_url:
            # Konverter til Base64 for at sikre at logoet kommer med ved "Save as PNG"
            b64_logo = get_base64_image(logo_url)
            
            fig.add_layout_image(dict(
                source=b64_logo, xref="x", yref="y",
                x=row['#'], y=row[metric],
                sizex=0.5, 
                sizey=y_span * 0.35,
                xanchor="center", 
                # Ankerpunkt skifter baseret på om aksen er vendt
                yanchor="bottom" if not is_ppda else "top"
            ))

    # Hover-lag (usynligt scatter)
    fig.add_trace(go.Scatter(
        x=df_merged['#'], y=df_merged[metric],
        mode='markers', 
        marker=dict(size=45, opacity=0), 
        hovertext=df_merged['HOLD_NAVN'],
        hovertemplate="<b>%{hovertext}</b><br>Placering: %{x}<br>"+label+": %{y:.2f}<extra></extra>"
    ))

    fig.update_layout(
        height=650, 
        margin=dict(t=30, b=60, l=60, r=40),
        xaxis=dict(
            title="<b>Placering</b>", 
            tickmode='linear', 
            range=[0.4, 12.6],
            gridcolor="#f0f0f0",
            linecolor='black',
            zeroline=False
        ),
        yaxis=dict(
            title=f"<b>{label}</b>", 
            gridcolor="#f0f0f0",
            autorange="reversed" if is_ppda else True,
            zeroline=False,
            linecolor='black'
        ),
        plot_bgcolor='white'
    )
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

# --- 3. HOVEDFUNKTION ---

def vis_side():
    df_opta, df_wy = load_data()
    if df_opta is None or df_opta.empty: return

    df_opta.columns = [c.upper() for c in df_opta.columns]

    # Beregn Tabel baseret på Opta UUIDs
    stats = {}
    for _, row in df_opta.sort_values('MATCH_DATE_FULL').iterrows():
        status = str(row.get('MATCH_STATUS', '')).lower()
        if any(x in status for x in ['played', 'full', 'finish']):
            h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
            for uuid in [h_uuid, a_uuid]:
                if uuid not in stats: stats[uuid] = {'P': 0, 'MD': 0}
            
            h_g, a_g = int(row.get('TOTAL_HOME_SCORE', 0)), int(row.get('TOTAL_AWAY_SCORE', 0))
            stats[h_uuid]['MD'] += (h_g - a_g); stats[a_uuid]['MD'] += (a_g - h_g)
            if h_g > a_g: stats[h_uuid]['P'] += 3
            elif a_g > h_g: stats[a_uuid]['P'] += 3
            else: stats[h_uuid]['P'] += 1; stats[a_uuid]['P'] += 1

    df_liga = pd.DataFrame.from_dict(stats, orient='index').reset_index()
    df_liga.rename(columns={'index': 'OPTA_UUID'}, inplace=True)
    df_liga = df_liga.sort_values(['P', 'MD'], ascending=False).reset_index(drop=True)
    df_liga['#'] = df_liga.index + 1

    # Merge performance data via TEAMS mapping
    final_data = []
    for _, row in df_liga.iterrows():
        opt_uuid = row['OPTA_UUID']
        
        # Find team i mapping
        team_info = next((info for name, info in TEAMS.items() if info.get('opta_uuid') == opt_uuid), None)
        team_display_name = next((name for name, info in TEAMS.items() if info.get('opta_uuid') == opt_uuid), "Ukendt")
        
        if team_info:
            wy_id = team_info.get('team_wyid')
            perf = df_wy[df_wy['TEAM_WYID'] == wy_id]
            
            entry = {
                '#': row['#'],
                'HOLD_NAVN': team_display_name,
                'LOGO_URL': team_info.get('logo'),
                'XG': perf['XG'].iloc[0] if not perf.empty else np.nan,
                'SHOTS': perf['SHOTS'].iloc[0] if not perf.empty else np.nan,
                'GOALS': perf['GOALS'].iloc[0] if not perf.empty else np.nan,
                'PPDA': perf['PPDA'].iloc[0] if not perf.empty else np.nan,
                'PASSES': perf['PASSES'].iloc[0] if not perf.empty else np.nan
            }
            final_data.append(entry)

    df_final = pd.DataFrame(final_data)

    # --- TOPBAR LAYOUT ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Betinia Ligaen: Placering vs. Performance")
    with col2:
        metric_map = {
            "xG (Expected Goals)": "XG", 
            "Mål": "GOALS", 
            "Skud": "SHOTS", 
            "Pres (PPDA)": "PPDA", 
            "Afleveringer": "PASSES"
        }
        sel_metric = st.selectbox("", list(metric_map.keys()), label_visibility="collapsed")
    
    draw_position_performance_chart(df_final, metric_map[sel_metric], sel_metric)

if __name__ == "__main__":
    vis_side()
