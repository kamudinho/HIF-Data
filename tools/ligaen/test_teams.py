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

def hent_kampe(uuid, df_opta):
    hold_kampe = df_opta[(df_opta['CONTESTANTHOME_OPTAUUID'] == uuid) | (df_opta['CONTESTANTAWAY_OPTAUUID'] == uuid)]
    played = hold_kampe[hold_kampe['MATCH_STATUS'].str.lower().isin(['played', 'full-time', 'finished'])].sort_values('MATCH_DATE_FULL', ascending=False)
    future = hold_kampe[~hold_kampe['MATCH_STATUS'].str.lower().isin(['played', 'full-time', 'finished'])].sort_values('MATCH_DATE_FULL', ascending=True)
    return (played.iloc[0] if not played.empty else None), (future.iloc[0] if not future.empty else None)

def format_kamp(kamp, hold_uuid):
    if kamp is None: return "-"
    is_home = kamp['CONTESTANTHOME_OPTAUUID'] == hold_uuid
    modstander = kamp['CONTESTANTAWAY_NAME'] if is_home else kamp['CONTESTANTHOME_NAME']
    res = f"{kamp['TOTAL_HOME_SCORE']}-{kamp['TOTAL_AWAY_SCORE']}" if 'TOTAL_HOME_SCORE' in kamp and pd.notnull(kamp['TOTAL_HOME_SCORE']) else "vs"
    return f"{modstander} ({res})"

# --- 2. BEREGNINGS FUNKTIONER & GRAF ---
def beregn_tabel(df_matches):
    stats = {}
    for _, row in df_matches.iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats: stats[uuid] = {'HOLD': name, 'UUID': uuid, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': ""}
        if str(row['MATCH_STATUS']).lower() in ['played', 'full-time', 'finished']:
            h_g, a_g = int(row['TOTAL_HOME_SCORE'] or 0), int(row['TOTAL_AWAY_SCORE'] or 0)
            for u, gf, ga in [(h_uuid, h_g, a_g), (a_uuid, a_g, h_g)]:
                stats[u]['K'] += 1; stats[u]['M+'] += gf; stats[u]['M-'] += ga
                if gf > ga: stats[u]['P'] += 3; stats[u]['V'] += 1; stats[u]['FORM'] += 'V'
                elif gf == ga: stats[u]['P'] += 1; stats[u]['U'] += 1; stats[u]['FORM'] += 'U'
                else: stats[u]['T'] += 1; stats[u]['FORM'] += 'T'
    df = pd.DataFrame(stats.values())
    df['MD'] = df['M+'] - df['M-']
    return df.sort_values(['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)

def draw_h2h_chart(team1, team2, metrics, labels, df_wy, chart_key, df_liga):
    fig = go.Figure()
    col_width, gap = 0.18, 0.05
    d1 = df_wy[df_wy['TEAMNAME'].str.contains(team1, case=False, na=False)]
    d2 = df_wy[df_wy['TEAMNAME'].str.contains(team2, case=False, na=False)]
    
    for i, m in enumerate(metrics):
        suffix = f"{i+1}" if i > 0 else ""
        # Her tjekker vi om kolonnen eksisterer, ellers returneres 0
        v1 = float(d1[m.upper()].iloc[0]) if not d1.empty and m.upper() in d1.columns else 0.0
        v2 = float(d2[m.upper()].iloc[0]) if not d2.empty and m.upper() in d2.columns else 0.0
        
        fig.add_trace(go.Bar(x=[0, 1], y=[v1, v2], marker_color=[TEAM_COLORS.get(team1, {}).get("primary", "#df003b"), TEAM_COLORS.get(team2, {}).get("primary", "#0056a3")], width=0.7, xaxis=f"x{suffix}", yaxis=f"y{suffix}"))
        fig.add_annotation(dict(x=0.5, y=-0.2, xref=f"x{suffix} domain", yref=f"y{suffix} domain", text=f"<b>{labels[i]}</b>", showarrow=False))
        fig.update_layout({f"xaxis{suffix}": dict(domain=[i*(col_width+gap), i*(col_width+gap)+col_width], showticklabels=False), f"yaxis{suffix}": dict(visible=False)})
    
    fig.update_layout(height=380, margin=dict(t=50, b=50), plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True, key=chart_key)

def render_kamp_boks(kamp):
    # Logoer og navne
    home_name = kamp['CONTESTANTHOME_NAME']
    away_name = kamp['CONTESTANTAWAY_NAME']
    home_logo = get_logo_html(kamp['CONTESTANTHOME_OPTAUUID'])
    away_logo = get_logo_html(kamp['CONTESTANTAWAY_OPTAUUID'])
    
    # Resultat eller tidspunkt
    res = f"{kamp['TOTAL_HOME_SCORE']}-{kamp['TOTAL_AWAY_SCORE']}" if pd.notnull(kamp['TOTAL_HOME_SCORE']) else "vs"
    
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px; background: #f0f2f6; border-radius: 8px; margin-bottom: 5px;">
        <span style="font-weight:bold;">{home_logo} {home_name}</span>
        <span style="background: #333; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;">{res}</span>
        <span style="font-weight:bold;">{away_name} {away_logo}</span>
    </div>
    """, unsafe_allow_html=True)

# --- 3. DATA LOADING ---
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

# --- 4. HOVEDFUNKTION ---
def vis_side():
    df_opta = load_liga_data()
    df_wy = get_wyscout_stats()
    played = df_opta[df_opta['MATCH_STATUS'].str.lower().isin(['played', 'full-time', 'finished'])].sort_values('MATCH_DATE_FULL')
    
    # Præcis 22 runder logik
    kamp_count = {}; cutoff_index = 0
    for i, row in played.iterrows():
        h, a = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        kamp_count[h] = kamp_count.get(h, 0) + 1; kamp_count[a] = kamp_count.get(a, 0) + 1
        if all(val >= 22 for val in kamp_count.values()): cutoff_index = played.index.get_loc(i); break
            
    gs_df = beregn_tabel(played.iloc[:cutoff_index + 1])
    slut_df = beregn_tabel(played)
    top6, bund6 = gs_df.head(6)['UUID'].tolist(), gs_df.tail(6)['UUID'].tolist()
    
    # Hjælpefunktion til at vise tabel
    def vis_tabel(df_in, filter_list):
        df = df_in.copy()
        if filter_list is not None: df = df[df['UUID'].isin(filter_list)]
        df.insert(0, '#', range(1, len(df) + 1))
        df.insert(1, ' ', [get_logo_html(u) for u in df['UUID']])
        df['FORM'] = df['FORM'].apply(style_form)
        st.write(df[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    # Hjælpefunktion til at vise kampe grafisk
    def render_kampe_for_runde(df_opta, runde_nr):
        runde_kampe = df_opta[df_opta['ROUND'] == runde_nr] 
        st.markdown(f"#### Runde {runde_nr}")
        for _, kamp in runde_kampe.iterrows():
            render_kamp_boks(kamp)

    t_gs, t_slut, t_h2h = st.tabs(["Grundspil", "Slutspil", "Head-to-head"])
    
    with t_gs: 
        vis_tabel(gs_df, None)
        
    with t_slut:
        c1, c2 = st.columns(2)
        with c1: 
            st.subheader("Oprykningsspil")
            vis_tabel(slut_df, top6)
            # Kald kampvisning her (Kræver at din df_opta har en 'ROUND' kolonne)
            render_kampe_for_runde(df_opta, 31) 
        with c2: 
            st.subheader("Nedrykningsspil")
            vis_tabel(slut_df, bund6)
            render_kampe_for_runde(df_opta, 31)
    with t_h2h:
        h_list = sorted(gs_df['HOLD'].tolist())
        c1, c2 = st.columns(2); t1 = c1.selectbox("Hold 1", h_list, index=0); t2 = c2.selectbox("Hold 2", [h for h in h_list if h != t1], index=0)
        tabs = st.tabs(["Generelt", "xG Stats", "Afslutninger", "Defensivt", "Spilopbygning"])
        with tabs[0]: draw_h2h_chart(t1, t2, ['SHOTS', 'GOALS', 'PPDA', 'MATCHTEMPO'], ['Skud', 'Mål', 'PPDA', 'Tempo'], df_wy, "gen", gs_df)
        with tabs[1]: draw_h2h_chart(t1, t2, ['XG', 'XGPERSHOT'], ['Total xG', 'xG pr. skud'], df_wy, "xg", gs_df)
        with tabs[2]: draw_h2h_chart(t1, t2, ['SHOTSONTARGET', 'SHOTSBLOCKED', 'SHOTSFROMBOX', 'SHOTSFROMDANGERZONE'], ['På mål', 'Blokeret', 'I feltet', 'Danger Zone'], df_wy, "shot", gs_df)
        with tabs[3]: draw_h2h_chart(t1, t2, ['INTERCEPTIONS', 'TACKLES', 'CLEARANCES'], ['Interc.', 'Tackler', 'Clearing'], df_wy, "def", gs_df)
        with tabs[4]: draw_h2h_chart(t1, t2, ['PASSES', 'CROSSESTOTAL', 'PROGRESSIVEPASSES', 'PASSTOFINALTHIRDS'], ['Aflev.', 'Indlæg', 'Progr.', 'Sidste 1/3'], df_wy, "pass", gs_df)

if __name__ == "__main__":
    st.markdown("<style>.league-table { width: 100%; }</style>", unsafe_allow_html=True)
    vis_side()
