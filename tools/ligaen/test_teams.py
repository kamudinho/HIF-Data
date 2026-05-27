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
    query = f"SELECT * FROM {db}.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'"
    df = conn.query(query)
    df.columns = [c.upper() for c in df.columns]
    df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'])
    return df

@st.cache_data(ttl=3600)
def get_wyscout_stats():
    conn = _get_snowflake_conn()
    db = "KLUB_HVIDOVREIF.AXIS"
    query = f"""
        SELECT t.TEAMNAME, AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, 
               AVG(adv.XGPERSHOT) as XGPERSHOT, AVG(adv.SHOTSONTARGET) as SHOTSONTARGET, 
               AVG(adv.SHOTSBLOCKED) as SHOTSBLOCKED, AVG(adv.SHOTSFROMBOX) as SHOTSFROMBOX, 
               AVG(adv.SHOTSFROMDANGERZONE) as SHOTSFROMDANGERZONE, AVG(md.INTERCEPTIONS) as INTERCEPTIONS, 
               AVG(md.TACKLES) as TACKLES, AVG(md.CLEARANCES) as CLEARANCES, AVG(mp.PASSES) as PASSES, 
               AVG(mp.CROSSESTOTAL) as CROSSESTOTAL, AVG(mp.PROGRESSIVEPASSES) as PROGRESSIVEPASSES, 
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

# --- 3. TABEL OG CHART FUNKTIONER ---
def beregn_tabel(df_matches, hold_filter=None):
    stats = {}
    for hold_navn, info in TEAMS.items():
        o_uuid = str(info.get('opta_uuid', '')).upper()
        if o_uuid:
            stats[o_uuid] = {'HOLD': hold_navn, 'UUID': o_uuid, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': ""}
    for _, row in df_matches.iterrows():
        h_uuid, a_uuid = str(row['CONTESTANTHOME_OPTAUUID']).upper(), str(row['CONTESTANTAWAY_OPTAUUID']).upper()
        h_g, a_g = int(row['TOTAL_HOME_SCORE'] or 0), int(row['TOTAL_AWAY_SCORE'] or 0)
        for uuid, g_for, g_against in [(h_uuid, h_g, a_g), (a_uuid, a_g, h_g)]:
            if uuid in stats:
                stats[uuid]['K'] += 1; stats[uuid]['M+'] += g_for; stats[uuid]['M-'] += g_against
                if g_for > g_against: stats[uuid]['P'] += 3; stats[uuid]['V'] += 1; stats[uuid]['FORM'] += 'V'
                elif g_for == g_against: stats[uuid]['P'] += 1; stats[uuid]['U'] += 1; stats[uuid]['FORM'] += 'U'
                else: stats[uuid]['T'] += 1; stats[uuid]['FORM'] += 'T'
    df = pd.DataFrame(stats.values())
    df = df[df['K'] > 0].copy()
    if hold_filter: df = df[df['UUID'].isin(hold_filter)]
    df['MD'] = df['M+'] - df['M-']
    df = df.sort_values(['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df.insert(0, '#', df.index + 1)
    return df

def draw_h2h_chart(team1, team2, metrics, labels, df_wy, chart_key, df_liga):
    fig = go.Figure()
    col_width, gap = 0.18, 0.05
    t1_data = df_liga[df_liga['HOLD'] == team1]
    t2_data = df_liga[df_liga['HOLD'] == team2]
    u1, u2 = t1_data['UUID'].values[0] if not t1_data.empty else None, t2_data['UUID'].values[0] if not t2_data.empty else None
    l1, l2 = get_logo_url(u1), get_logo_url(u2)
    for i, m in enumerate(metrics):
        suffix = f"{i+1}" if i > 0 else ""
        d1 = df_wy[df_wy['TEAMNAME'].str.contains(team1, case=False, na=False)]
        d2 = df_wy[df_wy['TEAMNAME'].str.contains(team2, case=False, na=False)]
        v1, v2 = float(d1[m.upper()].iloc[0] if not d1.empty and m.upper() in d1.columns else 0), float(d2[m.upper()].iloc[0] if not d2.empty and m.upper() in d2.columns else 0)
        fig.add_trace(go.Bar(x=[0, 1], y=[v1, v2], marker_color=[TEAM_COLORS.get(team1, {}).get("primary", "#df003b"), TEAM_COLORS.get(team2, {}).get("primary", "#0056a3")], width=0.7, xaxis=f"x{suffix}", yaxis=f"y{suffix}"))
        fig.add_annotation(dict(x=0, y=v1, xref=f"x{suffix}", yref=f"y{suffix}", text=f"<b>{v1:.1f}</b>", showarrow=False, yshift=15))
        fig.add_annotation(dict(x=1, y=v2, xref=f"x{suffix}", yref=f"y{suffix}", text=f"<b>{v2:.1f}</b>", showarrow=False, yshift=15))
        fig.add_annotation(dict(x=0.5, y=-0.2, xref=f"x{suffix} domain", yref=f"y{suffix} domain", text=f"<b>{labels[i]}</b>", showarrow=False))
        fig.update_layout({f"xaxis{suffix}": dict(domain=[i*(col_width+gap), i*(col_width+gap)+col_width], showticklabels=False), f"yaxis{suffix}": dict(visible=False)})
    fig.update_layout(height=350, margin=dict(t=80, b=50), plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True, key=chart_key)

# --- 4. HOVEDFUNKTION ---
def vis_side():
    df_opta = load_liga_data()
    df_wy = get_wyscout_stats()
    played = df_opta[df_opta['MATCH_STATUS'].str.lower().isin(['played', 'full-time', 'finished'])].sort_values('MATCH_DATE_FULL')
    
    gs_tabel = beregn_tabel(played.head(132)) 
    top6 = gs_tabel.head(6)['UUID'].tolist()
    bund6 = gs_tabel.tail(6)['UUID'].tolist()
    
    t_gs, t_op, t_ned, t_h2h = st.tabs(["Grundspil", "Oprykningsspil", "Nedrykningsspil", "Head-to-head"])

    with t_gs: 
        d = gs_tabel.copy(); d.insert(1, ' ', [get_logo_html(u) for u in d['UUID']]); d['FORM'] = d['FORM'].apply(style_form)
        st.write(d[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)
    with t_op: st.write("Oprykningsspil (top 6)") # Tilføj render_tabel logik her
    with t_ned: st.write("Nedrykningsspil (bund 6)")
    with t_h2h:
        h_list = sorted(gs_tabel['HOLD'].tolist())
        c1, c2 = st.columns(2); t1 = c1.selectbox("Hold 1", h_list, index=0); t2 = c2.selectbox("Hold 2", [h for h in h_list if h != t1], index=0)
        draw_h2h_chart(t1, t2, ['SHOTS', 'GOALS', 'XG'], ['Skud', 'Mål', 'xG'], df_wy, "h2h", gs_tabel)

if __name__ == "__main__":
    st.markdown("<style>.league-table { width: 100%; }</style>", unsafe_allow_html=True)
    vis_side()
