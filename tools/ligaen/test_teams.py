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
    # Tilføjet en onerror for at skjule ødelagte links
    return f'<img src="{url}" width="25" style="border-radius: 50%;" onerror="this.style.display=\'none\'">' if url else ""

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
    df = conn.query("SELECT * FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'")
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

# --- 3. BEREGNINGS LOGIK ---
def beregn_tabel_data(df_matches):
    """Beregner stilling for et givent datasæt af kampe"""
    stats = {}
    for _, row in df_matches.sort_values('MATCH_DATE_FULL').iterrows():
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
    
    df = pd.DataFrame(stats.values())
    df['MD'] = df['M+'] - df['M-']
    return df.sort_values(['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)

def draw_h2h_chart(team1, team2, metrics, labels, df_wy, chart_key, df_liga):
    fig = go.Figure()
    col_width, gap = 0.18, 0.05
    t1_data = df_liga[df_liga['HOLD'] == team1]; t2_data = df_liga[df_liga['HOLD'] == team2]
    u1 = t1_data['UUID'].values[0] if not t1_data.empty else None
    u2 = t2_data['UUID'].values[0] if not t2_data.empty else None
    l1, l2 = get_logo_url(u1), get_logo_url(u2)
    
    for i, m in enumerate(metrics):
        suffix = f"{i+1}" if i > 0 else ""
        # Præcis matchning (B.93 fix)
        d1 = df_wy[df_wy['TEAMNAME'].str.strip().str.lower() == team1.lower()]
        d2 = df_wy[df_wy['TEAMNAME'].str.strip().str.lower() == team2.lower()]
        v1, v2 = float(d1[m.upper()].iloc[0] if not d1.empty and m.upper() in d1.columns else 0), float(d2[m.upper()].iloc[0] if not d2.empty and m.upper() in d2.columns else 0)
        
        fig.add_trace(go.Bar(x=[0, 1], y=[v1, v2], marker_color=[TEAM_COLORS.get(team1, {}).get("primary", "#df003b"), TEAM_COLORS.get(team2, {}).get("primary", "#0056a3")], width=0.7, xaxis=f"x{suffix}", yaxis=f"y{suffix}"))
        fig.add_annotation(dict(x=0, y=v1, xref=f"x{suffix}", yref=f"y{suffix}", text=f"<b>{v1:.1f}</b>", showarrow=False, yshift=15))
        fig.add_annotation(dict(x=1, y=v2, xref=f"x{suffix}", yref=f"y{suffix}", text=f"<b>{v2:.1f}</b>", showarrow=False, yshift=15))
        fig.add_annotation(dict(x=0.5, y=-0.2, xref=f"x{suffix} domain", yref=f"y{suffix} domain", text=f"<b>{labels[i]}</b>", showarrow=False))
        fig.update_layout({f"xaxis{suffix}": dict(domain=[i*(col_width+gap), i*(col_width+gap)+col_width], showticklabels=False), f"yaxis{suffix}": dict(visible=False)})
        
        if l1: fig.add_layout_image(dict(source=l1, xref=f"x{suffix}", yref="paper", x=0, y=1.2, sizex=0.2, sizey=0.2, xanchor="center", yanchor="bottom"))
        if l2: fig.add_layout_image(dict(source=l2, xref=f"x{suffix}", yref="paper", x=1, y=1.2, sizex=0.2, sizey=0.2, xanchor="center", yanchor="bottom"))
        
    fig.update_layout(height=400, margin=dict(t=120, b=50), plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True, key=chart_key)

# --- 4. HOVEDFUNKTION ---
def vis_side():
    df_opta = load_liga_data()
    df_opta.columns = [c.upper() for c in df_opta.columns]
    
    # 1. Grundspil (Første 22 runder pr. hold = 132 kampe i en 12-holds liga)
    # Vi sorterer på dato og tager de første 132 kampe
    played_all = df_opta[df_opta['MATCH_STATUS'].str.lower().isin(['played', 'full-time', 'finished'])].sort_values('MATCH_DATE_FULL')
    grundspil_kampe = played_all.head(132) 
    
    # 2. Beregn stillingen efter grundspillet for at finde top/bund 6
    df_grund = beregn_tabel_data(grundspil_kampe)
    top6_uuids = df_grund.head(6)['UUID'].tolist()
    bund6_uuids = df_grund.tail(6)['UUID'].tolist()
    
    # 3. Beregn Slutspil (Hele sæsonen)
    df_slut = beregn_tabel_data(played_all)
    
    # Tabs struktur
    t_gs, t_op, t_ned, t_h2h = st.tabs(["Grundspil", "Oprykningsspil", "Nedrykningsspil", "Head-to-head"])

    def render_tabel(df_in, filter_uuids=None):
        df = df_in.copy()
        if filter_uuids:
            df = df[df['UUID'].isin(filter_uuids)]
        
        df.insert(0, '#', range(1, len(df) + 1))
        df.insert(1, ' ', [get_logo_html(u) for u in df['UUID']])
        df['FORM'] = df['FORM'].apply(style_form)
        
        st.write(df[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(
            escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_gs: render_tabel(df_grund)
    with t_op: render_tabel(df_slut, filter_uuids=top6_uuids)
    with t_ned: render_tabel(df_slut, filter_uuids=bund6_uuids)
    with t_h2h:
        h_list = sorted(gs_tabel['HOLD'].tolist())
        c1, c2 = st.columns(2); t1 = c1.selectbox("Hold 1", h_list, index=0); t2 = c2.selectbox("Hold 2", [h for h in h_list if h != t1], index=0)
        tabs = st.tabs(["Generelt", "xG Stats", "Afslutninger", "Defensivt", "Spilopbygning"])
        with tabs[0]: draw_h2h_chart(t1, t2, ['SHOTS', 'GOALS', 'PPDA', 'MATCHTEMPO'], ['Skud', 'Mål', 'PPDA', 'Tempo'], df_wy, "gen", gs_tabel)
        with tabs[1]: draw_h2h_chart(t1, t2, ['XG', 'XGPERSHOT'], ['Total xG', 'xG pr. skud'], df_wy, "xg", gs_tabel)
        with tabs[2]: draw_h2h_chart(t1, t2, ['SHOTSONTARGET', 'SHOTSBLOCKED', 'SHOTSFROMBOX', 'SHOTSFROMDANGERZONE'], ['På mål', 'Blokeret', 'I feltet', 'Danger Zone'], df_wy, "shot", gs_tabel)
        with tabs[3]: draw_h2h_chart(t1, t2, ['INTERCEPTIONS', 'TACKLES', 'CLEARANCES'], ['Interc.', 'Tackler', 'Clearing'], df_wy, "def", gs_tabel)
        with tabs[4]: draw_h2h_chart(t1, t2, ['PASSES', 'CROSSESTOTAL', 'PROGRESSIVEPASSES', 'PASSTOFINALTHIRDS'], ['Aflev.', 'Indlæg', 'Progr.', 'Sidste 1/3'], df_wy, "pass", gs_tabel)

if __name__ == "__main__":
    st.markdown("<style>.league-table { width: 100%; border-collapse: collapse; } .league-table td { padding: 10px; border-bottom: 1px solid #ddd; }</style>", unsafe_allow_html=True)
    vis_side()
