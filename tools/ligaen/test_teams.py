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

# --- 2. GRAF FUNKTION ---
def draw_h2h_chart(team1, team2, metrics, labels, df_wy, chart_key, df_liga):
    fig = go.Figure()
    col_width, gap = 0.18, 0.05
    d1 = df_wy[df_wy['TEAMNAME'].str.strip().str.lower() == team1.lower()]
    d2 = df_wy[df_wy['TEAMNAME'].str.strip().str.lower() == team2.lower()]
    
    for i, m in enumerate(metrics):
        suffix = f"{i+1}" if i > 0 else ""
        v1 = float(d1[m.upper()].iloc[0] if not d1.empty and m.upper() in d1.columns else 0)
        v2 = float(d2[m.upper()].iloc[0] if not d2.empty and m.upper() in d2.columns else 0)
        
        fig.add_trace(go.Bar(x=[0, 1], y=[v1, v2], marker_color=[TEAM_COLORS.get(team1, {}).get("primary", "#df003b"), TEAM_COLORS.get(team2, {}).get("primary", "#0056a3")], width=0.7, xaxis=f"x{suffix}", yaxis=f"y{suffix}"))
        fig.add_annotation(dict(x=0.5, y=-0.2, xref=f"x{suffix} domain", yref=f"y{suffix} domain", text=f"<b>{labels[i]}</b>", showarrow=False))
        fig.update_layout({f"xaxis{suffix}": dict(domain=[i*(col_width+gap), i*(col_width+gap)+col_width], showticklabels=False), f"yaxis{suffix}": dict(visible=False)})
    
    fig.update_layout(height=350, margin=dict(t=50, b=50), plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig, use_container_width=True, key=chart_key)

# --- 3. DATA LOADING & BEREGNING ---
@st.cache_data(ttl=3600)
def load_data():
    conn = _get_snowflake_conn()
    df = conn.query(f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = 'dyjr458hcmrcy87fsabfsy87o'")
    df.columns = [c.upper() for c in df.columns]
    df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'])
    return df

@st.cache_data(ttl=3600)
def get_wyscout_stats():
    conn = _get_snowflake_conn()
    query = """
        SELECT t.TEAMNAME, AVG(adv.XG) as XG, AVG(adv.SHOTS) as SHOTS, AVG(adv.GOALS) as GOALS, 
               AVG(md.PPDA) as PPDA, AVG(mp.MATCHTEMPO) as MATCHTEMPO, AVG(adv.SHOTSONTARGET) as SHOTSONTARGET, 
               AVG(adv.SHOTSBLOCKED) as SHOTSBLOCKED, AVG(adv.SHOTSFROMBOX) as SHOTSFROMBOX, 
               AVG(adv.SHOTSFROMDANGERZONE) as SHOTSFROMDANGERZONE, AVG(md.INTERCEPTIONS) as INTERCEPTIONS, 
               AVG(md.TACKLES) as TACKLES, AVG(md.CLEARANCES) as CLEARANCES, AVG(mp.PASSES) as PASSES, 
               AVG(mp.CROSSESTOTAL) as CROSSESTOTAL, AVG(mp.PROGRESSIVEPASSES) as PROGRESSIVEPASSES, 
               AVG(mp.PASSTOFINALTHIRDS) as PASSTOFINALTHIRDS
        FROM KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMMATCHES tm 
        JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN KLUB_HVIDOVREIF.AXIS.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328
        GROUP BY t.TEAMNAME
    """
    return conn.query(query)

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

# --- HJÆLPEFUNKTION TIL KAMPE ---
def hent_kampe(uuid, df_opta):
    # Filtrer kampe for det specifikke hold
    hold_kampe = df_opta[(df_opta['CONTESTANTHOME_OPTAUUID'] == uuid) | (df_opta['CONTESTANTAWAY_OPTAUUID'] == uuid)]
    
    played = hold_kampe[hold_kampe['MATCH_STATUS'].str.lower().isin(['played', 'full-time', 'finished'])].sort_values('MATCH_DATE_FULL', ascending=False)
    future = hold_kampe[~hold_kampe['MATCH_STATUS'].str.lower().isin(['played', 'full-time', 'finished'])].sort_values('MATCH_DATE_FULL', ascending=True)
    
    sidste = played.iloc[0] if not played.empty else None
    naeste = future.iloc[0] if not future.empty else None
    
    return sidste, naeste

def format_kamp(kamp, hold_uuid):
    if kamp is None: return "Ingen kamp"
    is_home = kamp['CONTESTANTHOME_OPTAUUID'] == hold_uuid
    modstander = kamp['CONTESTANTAWAY_NAME'] if is_home else kamp['CONTESTANTHOME_NAME']
    logo = get_logo_html(kamp['CONTESTANTAWAY_OPTAUUID'] if is_home else kamp['CONTESTANTHOME_OPTAUUID'])
    res = f"{kamp['TOTAL_HOME_SCORE']}-{kamp['TOTAL_AWAY_SCORE']}" if 'TOTAL_HOME_SCORE' in kamp else "vs"
    return f"{logo} {modstander} ({res})"

# --- RENDER TABEL OPDATERING ---
def render_tabel_med_kampe(df_in, filter_list, df_opta):
    df = df_in.copy()
    if filter_list is not None: df = df[df['UUID'].isin(filter_list)]
    df.insert(0, '#', range(1, len(df) + 1))
    df.insert(1, ' ', [get_logo_html(u) for u in df['UUID']])
    df['FORM'] = df['FORM'].apply(style_form)
    
    # Vis selve tabellen
    st.write(df[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)
    
    # Tilføj kampe-sektion
    st.markdown("##### Sidste og næste kamp")
    kampe_data = []
    for uuid in df['UUID']:
        s, n = hent_kampe(uuid, df_opta)
        kampe_data.append({"HOLD": df[df['UUID']==uuid]['HOLD'].values[0], "SIDSTE": format_kamp(s, uuid), "NÆSTE": format_kamp(n, uuid)})
    
    st.table(pd.DataFrame(kampe_data))

# --- 4. HOVEDFUNKTION ---
def vis_side():
    played = load_data()
    df_wy = get_wyscout_stats()
    
    # --- PRÆCIS 22 RUNDER LOGIK ---
    # Vi finder de første 22 kampe for hvert hold
    played = played.sort_values('MATCH_DATE_FULL')
    
    # Lav en liste over alle hold
    alle_hold = pd.concat([played['CONTESTANTHOME_OPTAUUID'], played['CONTESTANTAWAY_OPTAUUID']]).unique()
    
    # Find index for den kamp hvor alle hold har spillet 22 kampe
    # Vi tager den kamp, hvor det 22. hold har spillet sin 22. kamp
    kamp_count = {}
    cutoff_index = 0
    for i, row in played.iterrows():
        h, a = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        kamp_count[h] = kamp_count.get(h, 0) + 1
        kamp_count[a] = kamp_count.get(a, 0) + 1
        
        # Når alle hold har nået 22 kampe, er grundspillet slut
        if all(val >= 22 for val in kamp_count.values()):
            cutoff_index = played.index.get_loc(i)
            break
            
    gs_df = beregn_tabel(played.iloc[:cutoff_index + 1])
    slut_df = beregn_tabel(played)
    # -------------------------------
    
    top6_uuids = gs_df.head(6)['UUID'].tolist()
    bund6_uuids = gs_df.tail(6)['UUID'].tolist()
    
    t_gs, t_slut, t_h2h = st.tabs(["Grundspil", "Slutspil", "Head-to-head"])

    def render_tabel(df_in, filter_list=None):
        df = df_in.copy()
        if filter_list is not None: df = df[df['UUID'].isin(filter_list)]
        df.insert(0, '#', range(1, len(df) + 1))
        df.insert(1, ' ', [get_logo_html(u) for u in df['UUID']])
        df['FORM'] = df['FORM'].apply(style_form)
        st.write(df[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_gs: 
        render_tabel(gs_df)

    with t_slut:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Oprykningsspil")
            render_tabel_med_kampe(slut_df, top6_uuids, df_opta)
        with c2:
            st.subheader("Nedrykningsspil")
            render_tabel_med_kampe(slut_df, bund6_uuids, df_opta)
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
    st.markdown("<style>.league-table { width: 100%; border-collapse: collapse; } .league-table td { padding: 8px; border-bottom: 1px solid #ddd; }</style>", unsafe_allow_html=True)
    vis_side()
