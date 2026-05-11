import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. HJÆLPEFUNKTIONER ---

def get_logo_url(opta_uuid):
    return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

def get_logo_html(uuid):
    url = get_logo_url(uuid)
    return f'<img src="{url}" width="20">' if url else ""

def style_form(f):
    if not f: return ""
    res = ""
    for char in f[-5:]:
        color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
        res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
    return res

# --- 2. DATA LOADING (OPDATERET TIL AT HÅNDTERE SPLIT) ---

@st.cache_data(ttl=3600)
def load_liga_data():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    # Henter alle kampe for sæsonen
    query = f"""
        SELECT *, 
        CASE 
            WHEN ROUND <= 22 THEN 'Grundspil'
            ELSE 'Slutspil'
        END as PHASE
        FROM {db}.OPTA_MATCHINFO 
        WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'
        ORDER BY ROUND ASC, MATCH_DATE_FULL ASC
    """
    return conn.query(query)

@st.cache_data(ttl=3600)
def get_wyscout_stats():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    # Vi sikrer os at vi henter data for den nuværende NordicBet Liga sæson
    query = f"""
        SELECT t.TEAMNAME, 
               AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, 
               AVG(md.INTERCEPTIONS) as INTERCEPTIONS, AVG(md.PPDA) as PPDA, 
               AVG(mp.PASSES) as PASSES, AVG(mp.MATCHTEMPO) as MATCHTEMPO
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        JOIN {db}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328
        GROUP BY t.TEAMNAME
    """
    return conn.query(query)

# --- 3. CHART FUNKTION ---

def draw_logo_position_chart(df_wy, metric, label, chart_key):
    m_upper = metric.upper()
    df_plot = df_wy.dropna(subset=[m_upper]).copy()
    df_plot = df_plot.sort_values(m_upper).reset_index()
    
    fig = go.Figure()
    y_values = np.linspace(0.2, 0.8, len(df_plot))

    for i, row in df_plot.iterrows():
        team_name = row['TEAMNAME']
        logo_url = next((info['logo'] for t_name, info in TEAMS.items() if t_name.lower() in team_name.lower()), "")
        
        if logo_url:
            fig.add_layout_image(dict(
                source=logo_url, xref="x", yref="y",
                x=row[m_upper], y=y_values[i],
                sizex=0.08 * (df_plot[m_upper].max() - df_plot[m_upper].min() if len(df_plot) > 1 else 1), 
                sizey=0.18, xanchor="center", yanchor="middle"
            ))

    fig.add_trace(go.Scatter(
        x=df_plot[m_upper], y=y_values, mode='markers',
        marker=dict(size=20, opacity=0),
        hovertext=df_plot['TEAMNAME'],
        hovertemplate="<b>%{hovertext}</b><br>Værdi: %{x:.2f}<extra></extra>"
    ))

    fig.update_layout(
        height=180, margin=dict(t=30, b=30, l=10, r=10),
        xaxis=dict(showgrid=True, gridcolor="#eee", title=label),
        yaxis=dict(showticklabels=False, showgrid=False, range=[0, 1]),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=chart_key)

# --- 4. HOVEDFUNKTION ---

def vis_side(dp_unused=None):
    df_opta = load_liga_data()
    df_wy = get_wyscout_stats()

    if df_opta is None or df_opta.empty:
        st.warning("Ingen kampdata fundet."); return

    df_opta.columns = [c.upper() for c in df_opta.columns]
    
    # --- BEREGN TABEL (MED HENSYN TIL GRUNDSPIL/SLUTSPIL) ---
    stats = {}
    for _, row in df_opta.sort_values('ROUND').iterrows():
        status = str(row.get('MATCH_STATUS', '')).lower()
        if any(x in status for x in ['played', 'full', 'finish']):
            h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
            for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
                if uuid not in stats:
                    stats[uuid] = {'HOLD': name, 'P': 0, 'MD': 0, 'K': 0, 'FORM': "", 'UUID': uuid}
            
            h_g, a_g = int(row['TOTAL_HOME_SCORE']), int(row['TOTAL_AWAY_SCORE'])
            stats[h_uuid]['K'] += 1; stats[a_uuid]['K'] += 1
            stats[h_uuid]['MD'] += (h_g - a_g); stats[a_uuid]['MD'] += (a_g - h_g)
            
            if h_g > a_g:
                stats[h_uuid]['P'] += 3; stats[h_uuid]['FORM'] += 'V'; stats[a_uuid]['FORM'] += 'T'
            elif a_g > h_g:
                stats[a_uuid]['P'] += 3; stats[a_uuid]['FORM'] += 'V'; stats[h_uuid]['FORM'] += 'T'
            else:
                stats[h_uuid]['P'] += 1; stats[a_uuid]['P'] += 1; stats[h_uuid]['FORM'] += 'U'; stats[a_uuid]['FORM'] += 'U'

    df_liga = pd.DataFrame(stats.values()).sort_values(['P', 'MD'], ascending=False).reset_index(drop=True)
    
    # Del op i opryknings- og nedrykningsspil (Top 6 / Bund 6)
    opryk = df_liga.head(6).copy()
    nedryk = df_liga.tail(6).copy()

    # --- UI ---
    st.title("NordicBet Liga Performance")
    
    t_pos, t_tabel = st.tabs(["Position Performance", "Ligatabel (Split)"])

    with t_pos:
        cat = st.selectbox("Vælg Metric", ["Offensivt", "Defensivt", "Spilopbygning"])
        if cat == "Offensivt":
            draw_logo_position_chart(df_wy, 'XG', 'Expected Goals', 'pos_xg')
            draw_logo_position_chart(df_wy, 'GOALS', 'Mål', 'pos_goals')
        elif cat == "Defensivt":
            draw_logo_position_chart(df_wy, 'PPDA', 'PPDA (Pres)', 'pos_ppda')
            draw_logo_position_chart(df_wy, 'INTERCEPTIONS', 'Erobringer', 'pos_int')
        else:
            draw_logo_position_chart(df_wy, 'PASSES', 'Afleveringer', 'pos_pass')
            draw_logo_position_chart(df_wy, 'MATCHTEMPO', 'Tempo', 'pos_tempo')

    with t_tabel:
        st.subheader("Oprykningsspil (Top 6)")
        opryk.insert(1, ' ', [get_logo_html(u) for u in opryk['UUID']])
        opryk['FORM'] = opryk['FORM'].apply(style_form)
        st.write(opryk[['HOLD', ' ', 'K', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, border=0, classes='league-table'), unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.subheader("Nedrykningsspil (Bund 6)")
        nedryk.insert(1, ' ', [get_logo_html(u) for u in nedryk['UUID']])
        nedryk['FORM'] = nedryk['FORM'].apply(style_form)
        st.write(nedryk[['HOLD', ' ', 'K', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, border=0, classes='league-table'), unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
