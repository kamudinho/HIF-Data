import streamlit as st
import pandas as pd
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

# --- 2. DATA LOADING ---

@st.cache_data(ttl=3600)
def load_liga_data():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    # Låst til din specifikke 1. division UUID
    query = f"SELECT * FROM {db}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'"
    return conn.query(query)

@st.cache_data(ttl=3600)
def get_wyscout_stats():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    query = f"""
        SELECT t.TEAMNAME, 
               AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, 
               AVG(adv.XGPERSHOT) as XGPERSHOT, AVG(adv.SHOTSONTARGET) as SHOTSONTARGET, 
               AVG(adv.SHOTSBLOCKED) as SHOTSBLOCKED, AVG(adv.SHOTSOUTSIDEBOX) as SHOTSOUTSIDEBOX, 
               AVG(adv.SHOTSFROMBOX) as SHOTSFROMBOX, AVG(adv.SHOTSFROMBOXONTARGET) as SHOTSFROMBOXONTARGET,
               AVG(adv.SHOTSFROMDANGERZONE) as SHOTSFROMDANGERZONE,
               AVG(md.INTERCEPTIONS) as INTERCEPTIONS, AVG(md.TACKLES) as TACKLES, 
               AVG(md.CLEARANCES) as CLEARANCES, AVG(md.PPDA) as PPDA, 
               AVG(mp.PASSES) as PASSES, AVG(mp.CROSSESTOTAL) as CROSSESTOTAL, 
               AVG(mp.FORWARDPASSES) as FORWARDPASSES, AVG(mp.PROGRESSIVEPASSES) as PROGRESSIVEPASSES, 
               AVG(mp.PASSTOFINALTHIRDS) as PASSTOFINALTHIRDS, AVG(mp.MATCHTEMPO) as MATCHTEMPO
        FROM {db}.WYSCOUT_TEAMMATCHES tm 
        JOIN {db}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {db}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328
        GROUP BY t.TEAMNAME
    """
    return conn.query(query)

# --- 3. DEN NYE LOGO-POSITION CHART FUNKTION ---

def draw_logo_position_chart(df_wy, metric, label, chart_key):
    """
    Tegner en horisontal akse hvor alle hold i ligaen er placeret som logoer
    baseret på den valgte metric.
    """
    m_upper = metric.upper()
    # Rens data og sorter
    df_plot = df_wy.dropna(subset=[m_upper]).copy()
    df_plot = df_plot.sort_values(m_upper).reset_index()
    
    fig = go.Figure()

    # Vi spreder dem lidt ud på y-aksen (0 til 1) så de ikke overlapper for meget
    # men stadig ser ud til at ligge på en linje
    y_values = np.linspace(0.2, 0.8, len(df_plot))

    for i, row in df_plot.iterrows():
        # Find logo via TEAMS mapping
        team_name = row['TEAMNAME']
        logo_url = next((info['logo'] for t_name, info in TEAMS.items() if t_name.lower() in team_name.lower()), "")
        
        if logo_url:
            fig.add_layout_image(
                dict(
                    source=logo_url,
                    xref="x", yref="y",
                    x=row[m_upper], y=y_values[i],
                    sizex=0.08 * (df_plot[m_upper].max() - df_plot[m_upper].min()), 
                    sizey=0.15,
                    xanchor="center", yanchor="middle"
                )
            )

    # Tilføj usynlige punkter for hover-effekt
    fig.add_trace(go.Scatter(
        x=df_plot[m_upper], y=y_values,
        mode='markers',
        marker=dict(size=20, opacity=0),
        hovertext=df_plot['TEAMNAME'],
        hovertemplate="<b>%{hovertext}</b><br>Værdi: %{x:.2f}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(text=f"Ligaplacering: {label}", font=dict(size=14, color="#555")),
        height=200,
        margin=dict(t=40, b=40, l=20, r=20),
        xaxis=dict(showgrid=True, gridcolor="#eee", zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, range=[0, 1]),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=chart_key)

# --- 4. HOVEDFUNKTION ---

def vis_side(dp_unused=None):
    try:
        df_opta = load_liga_data()
        df_wy = get_wyscout_stats()
    except Exception as e:
        st.error(f"Fejl ved hentning af data: {e}")
        return

    if df_opta is None or df_opta.empty:
        st.warning("Ingen kampdata fundet."); return

    df_opta.columns = [c.upper() for c in df_opta.columns]
    df_opta['MATCH_DATE_FULL'] = pd.to_datetime(df_opta['MATCH_DATE_FULL'])

    # (Tabel-beregninger bibeholdes fra din oprindelige kode...)
    stats = {}
    for _, row in df_opta.sort_values('MATCH_DATE_FULL').iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid}
        status = str(row['MATCH_STATUS']).strip().lower()
        if status in ['played', 'full-time', 'finished']:
            h_g, a_g = int(row['TOTAL_HOME_SCORE'] or 0), int(row['TOTAL_AWAY_SCORE'] or 0)
            stats[h_uuid]['K'] += 1; stats[a_uuid]['K'] += 1
            stats[h_uuid]['M+'] += h_g; stats[h_uuid]['M-'] += a_g
            stats[a_uuid]['M+'] += a_g; stats[a_uuid]['M-'] += h_g
            if h_g > a_g:
                stats[h_uuid]['P'] += 3; stats[h_uuid]['V'] += 1; stats[h_uuid]['FORM'] += 'V'; stats[a_uuid]['T'] += 1; stats[a_uuid]['FORM'] += 'T'
            elif a_g > h_g:
                stats[a_uuid]['P'] += 3; stats[a_uuid]['V'] += 1; stats[a_uuid]['FORM'] += 'V'; stats[h_uuid]['T'] += 1; stats[h_uuid]['FORM'] += 'T'
            else:
                stats[h_uuid]['P'] += 1; stats[a_uuid]['P'] += 1; stats[h_uuid]['U'] += 1; stats[a_uuid]['U'] += 1; stats[h_uuid]['FORM'] += 'U'; stats[a_uuid]['FORM'] += 'U'

    df_liga = pd.DataFrame(stats.values()).sort_values(['P', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    t_liga, t_pos = st.tabs(["Ligaoversigt", "Position Performance"])

    with t_liga:
        # (Din eksisterende tabel-visning...)
        st.markdown("<style>.league-table { width: 100%; border-collapse: collapse; }</style>", unsafe_allow_html=True)
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        st.write(df_disp[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'P', 'FORM']].to_html(escape=False, index=False, border=0, classes='league-table'), unsafe_allow_html=True)

    with t_pos:
        st.info("Se hvordan holdene ligger placeret i forhold til hinanden på tværs af ligaen.")
        
        # Dropdown til at styre kategorien
        cat = st.selectbox("Vælg kategori", ["Offensivt", "Defensivt", "Spilopbygning"])
        
        if cat == "Offensivt":
            draw_logo_position_chart(df_wy, 'XG', 'Expected Goals (Avg)', 'pos_xg')
            draw_logo_position_chart(df_wy, 'SHOTS', 'Skud pr. kamp (Avg)', 'pos_shots')
        elif cat == "Defensivt":
            draw_logo_position_chart(df_wy, 'PPDA', 'PPDA (Højt pres)', 'pos_ppda')
            draw_logo_position_chart(df_wy, 'INTERCEPTIONS', 'Erobringer (Avg)', 'pos_int')
        else:
            draw_logo_position_chart(df_wy, 'PASSES', 'Afleveringer (Avg)', 'pos_pass')
            draw_logo_position_chart(df_wy, 'MATCHTEMPO', 'Tempo (Aktioner/min)', 'pos_tempo')

if __name__ == "__main__":
    vis_side()
