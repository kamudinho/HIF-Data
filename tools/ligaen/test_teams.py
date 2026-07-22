import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- IMPORT DYNAMISKE KONSTANTER OG MAPPINGS ---
from data.utils.team_mapping import (
    SEASONS,
    COMPETITIONS,
    SEASON_LEAGUE_MAPPER,
    TEAMS,
    TEAM_COLORS,
    COMPETITION_NAME as DEFAULT_COMP,
    TOURNAMENTCALENDAR_NAME as DEFAULT_SEASON
)
from data.data_load import _get_snowflake_conn

# --- 1. HJÆLPEFUNKTIONER OG LOOKUPS ---

def get_team_info_by_opta_uuid(opta_uuid):
    """Finder holdets stamdata ud fra Opta UUID."""
    for team_name, info in TEAMS.items():
        if info.get('opta_uuid') == opta_uuid:
            return team_name, info
    return None, {}

def get_logo_url(opta_uuid):
    _, info = get_team_info_by_opta_uuid(opta_uuid)
    return info.get('logo', '')

def get_logo_html(uuid):
    url = get_logo_url(uuid)
    return f'<img src="{url}" width="20" style="vertical-align:middle;">' if url else ""

def style_form(f):
    if not f: return ""
    res = ""
    for char in str(f)[-5:]:
        color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
        res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
    return res

def beregn_tabel(df_matches, valgt_saeson, valgt_turnering):
    """
    Beregner ligatabellen. Initialiserer altid samtlige hold fra team_mapping 
    for den valgte sæson og turnering, så holdene fremgår med 0 kampe/point 
    hvis der ikke er spilledata endnu.
    """
    stats = {}

    # 1. Hent alle forventede hold fra team_mapping
    forventede_hold_navne = SEASON_LEAGUE_MAPPER.get(valgt_saeson, {}).get(valgt_turnering, [])
    
    for hold_navn in forventede_hold_navne:
        team_info = TEAMS.get(hold_navn, {})
        opta_uuid = team_info.get('opta_uuid', hold_navn)
        
        stats[opta_uuid] = {
            'HOLD': hold_navn, 
            'UUID': opta_uuid, 
            'K': 0, 'V': 0, 'U': 0, 'T': 0, 
            'M+': 0, 'M-': 0, 'P': 0, 'FORM': ""
        }

    # 2. Opdater med data fra spillede kampe, hvis der er nogen
    if df_matches is not None and not df_matches.empty:
        for _, row in df_matches.iterrows():
            h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
            
            # Sikr at hold oprettes, hvis et hold i Opta-data ikke var i mapper
            for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
                if uuid not in stats: 
                    stats[uuid] = {
                        'HOLD': name, 'UUID': uuid, 
                        'K': 0, 'V': 0, 'U': 0, 'T': 0, 
                        'M+': 0, 'M-': 0, 'P': 0, 'FORM': ""
                    }
            
            if str(row['MATCH_STATUS']).lower() in ['played', 'full-time', 'finished']:
                h_g = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
                a_g = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
                
                for u, gf, ga in [(h_uuid, h_g, a_g), (a_uuid, a_g, h_g)]:
                    stats[u]['K'] += 1
                    stats[u]['M+'] += gf
                    stats[u]['M-'] += ga
                    if gf > ga: 
                        stats[u]['P'] += 3; stats[u]['V'] += 1; stats[u]['FORM'] += 'V'
                    elif gf == ga: 
                        stats[u]['P'] += 1; stats[u]['U'] += 1; stats[u]['FORM'] += 'U'
                    else: 
                        stats[u]['T'] += 1; stats[u]['FORM'] += 'T'
                
    df = pd.DataFrame(stats.values())
    if df.empty:
        return pd.DataFrame(columns=['HOLD', 'UUID', 'K', 'V', 'U', 'T', 'M+', 'M-', 'P', 'FORM', 'MD'])
    
    df['MD'] = df['M+'] - df['M-']
    return df.sort_values(['P', 'MD', 'M+', 'HOLD'], ascending=[False, False, False, True]).reset_index(drop=True)

# --- 2. GRAFER OG H2H ---

def get_team_color(team_name, color_type="primary", default="#0056a3"):
    for key, colors in TEAM_COLORS.items():
        if key.lower() in team_name.lower() or team_name.lower() in key.lower():
            return colors.get(color_type, default)
    return default

def draw_h2h_chart(team1_name, team2_name, metrics, labels, df_wy, chart_key):
    fig = go.Figure()
    col_width, gap = 0.18, 0.05
    
    d1 = df_wy[df_wy['TEAMNAME'].str.contains(team1_name, case=False, na=False)] if not df_wy.empty else pd.DataFrame()
    d2 = df_wy[df_wy['TEAMNAME'].str.contains(team2_name, case=False, na=False)] if not df_wy.empty else pd.DataFrame()
    
    color1 = get_team_color(team1_name, "primary", "#cc0000")
    color2 = get_team_color(team2_name, "primary", "#0056a3")

    # Hent logo-URL'er for begge hold
    _, info1 = get_team_info_by_opta_uuid(TEAMS.get(team1_name, {}).get('opta_uuid'))
    _, info2 = get_team_info_by_opta_uuid(TEAMS.get(team2_name, {}).get('opta_uuid'))
    logo1_url = info1.get('logo', '')
    logo2_url = info2.get('logo', '')

    images = []

    for i, m in enumerate(metrics):
        suffix = f"{i+1}" if i > 0 else ""
        
        v1 = float(d1[m.upper()].iloc[0]) if not d1.empty and m.upper() in d1.columns else 0.0
        v2 = float(d2[m.upper()].iloc[0]) if not d2.empty and m.upper() in d2.columns else 0.0
        
        txt1 = f"{v1:.2f}".rstrip('0').rstrip('.') if v1 % 1 != 0 else f"{int(v1)}"
        txt2 = f"{v2:.2f}".rstrip('0').rstrip('.') if v2 % 1 != 0 else f"{int(v2)}"

        fig.add_trace(go.Bar(
            x=[0, 1], 
            y=[v1, v2], 
            text=[txt1, txt2],
            textposition='outside',
            textfont=dict(size=12, color='black'),
            marker_color=[color1, color2], 
            width=0.7, 
            xaxis=f"x{suffix}", 
            yaxis=f"y{suffix}"
        ))
        
        # Kategori-teksten placeres i TOPPEN (y=1.20)
        fig.add_annotation(dict(
            x=0.5, y=1.20, 
            xref=f"x{suffix} domain", 
            yref=f"y{suffix} domain", 
            text=f"<b>{labels[i]}</b>", 
            showarrow=False,
            font=dict(size=13)
        ))
        
        # Logoer placeres under søjlerne
        if logo1_url:
            images.append(dict(
                source=logo1_url,
                xref=f"x{suffix}", yref=f"y{suffix} domain",
                x=0, y=-0.08,
                sizex=0.40, sizey=0.22,
                xanchor="center", yanchor="top",
                sizing="contain",
                layer="above"
            ))
            
        if logo2_url:
            images.append(dict(
                source=logo2_url,
                xref=f"x{suffix}", yref=f"y{suffix} domain",
                x=1, y=-0.08,
                sizex=0.40, sizey=0.22,
                xanchor="center", yanchor="top",
                sizing="contain",
                layer="above"
            ))

        max_val = max(v1, v2, 1.0) * 1.30
        
        fig.update_layout({
            f"xaxis{suffix}": dict(domain=[i*(col_width+gap), i*(col_width+gap)+col_width], showticklabels=False), 
            f"yaxis{suffix}": dict(visible=False, range=[0, max_val])
        })
    
    fig.update_layout(
        images=images,
        height=450, 
        margin=dict(t=70, b=90, l=10, r=10), 
        plot_bgcolor='rgba(0,0,0,0)', 
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True, key=chart_key)
# --- 3. UI KOMPONENTER ---

def render_kamp_boks(kamp):
    home_name = kamp['CONTESTANTHOME_NAME']
    away_name = kamp['CONTESTANTAWAY_NAME']
    home_logo = get_logo_html(kamp['CONTESTANTHOME_OPTAUUID'])
    away_logo = get_logo_html(kamp['CONTESTANTAWAY_OPTAUUID'])
    
    h_score = int(kamp['TOTAL_HOME_SCORE']) if pd.notnull(kamp['TOTAL_HOME_SCORE']) else None
    a_score = int(kamp['TOTAL_AWAY_SCORE']) if pd.notnull(kamp['TOTAL_AWAY_SCORE']) else None
    res = f"{h_score}-{a_score}" if h_score is not None else "vs"
    
    st.markdown(f"""
    <div style="
        display: flex; 
        align-items: center; 
        justify-content: space-between; 
        width: 100%; 
        background-color: #ffffff; 
        border: 1px solid #e0e0e0; 
        border-radius: 10px; 
        padding: 12px 15px; 
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <div style="flex: 1; display: flex; align-items: center; justify-content: flex-start; font-weight: 600;">
            <span style="margin-right: 8px;">{home_logo}</span> {home_name}
        </div>
        <div style="background-color: #262730; color: #ffffff; padding: 5px 15px; border-radius: 6px; font-weight: bold; margin: 0 15px;">
            {res}
        </div>
        <div style="flex: 1; display: flex; align-items: center; justify-content: flex-end; font-weight: 600;">
            {away_name} <span style="margin-left: 8px;">{away_logo}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 4. DATA LOADING ---

@st.cache_data(ttl=3600)
def load_liga_data(opta_calendar_uuid):
    if not opta_calendar_uuid:
        return pd.DataFrame()
        
    conn = _get_snowflake_conn()
    query = f"SELECT * FROM KLUB_HVIDOVREIF.AXIS.OPTA_MATCHINFO WHERE TOURNAMENTCALENDAR_OPTAUUID = '{opta_calendar_uuid}'"
    df = conn.query(query)
    df.columns = [c.upper() for c in df.columns]
    if not df.empty and 'MATCH_DATE_FULL' in df.columns:
        df['MATCH_DATE_FULL'] = pd.to_datetime(df['MATCH_DATE_FULL'])
    return df

@st.cache_data(ttl=3600)
def get_wyscout_stats(competition_wyid):
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
        WHERE tm.COMPETITION_WYID = {competition_wyid}
        GROUP BY t.TEAMNAME
    """
    return conn.query(query)

def vis_tabel(df_in, filter_list):
    df = df_in.copy()
    if df.empty:
        st.info("Ingen data tilgængelig.")
        return
    if filter_list is not None: 
        df = df[df['UUID'].isin(filter_list)]
    
    df.insert(0, '#', range(1, len(df) + 1))
    df.insert(1, ' ', [get_logo_html(u) for u in df['UUID']])
    df['FORM'] = df['FORM'].apply(style_form)
    st.write(df[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

def render_kampe_dynamisk(df_opta, filter_uuids):
    if df_opta.empty: return
    
    maske = (df_opta['CONTESTANTHOME_OPTAUUID'].isin(filter_uuids)) | \
            (df_opta['CONTESTANTAWAY_OPTAUUID'].isin(filter_uuids))
    
    relevante_kampe = df_opta[maske]
    if relevante_kampe.empty: return

    unikke_datoer = sorted(relevante_kampe['MATCH_DATE_FULL'].dt.date.unique(), reverse=True)
    if unikke_datoer:
        seneste_dato = unikke_datoer[0]
        st.markdown(f"##### Seneste spillerunde: {seneste_dato}")
        dagens_kampe = relevante_kampe[relevante_kampe['MATCH_DATE_FULL'].dt.date == seneste_dato]
        for _, kamp in dagens_kampe.iterrows():
            render_kamp_boks(kamp)

# --- 5. HOVEDSIDE ---

def vis_side():
    calendar_uuid = SEASONS.get(DEFAULT_SEASON, {}).get(DEFAULT_COMP)
    wyid = COMPETITIONS.get(DEFAULT_COMP, {}).get("wyid", 328)

    df_opta = load_liga_data(calendar_uuid)
    df_wy = get_wyscout_stats(wyid)

    st.title(DEFAULT_COMP)

    # Filtrer spillede kampe hvis der er data
    played = pd.DataFrame()
    if not df_opta.empty and 'MATCH_STATUS' in df_opta.columns:
        played = df_opta[df_opta['MATCH_STATUS'].str.lower().isin(['played', 'full-time', 'finished'])].sort_values('MATCH_DATE_FULL')
    
    cutoff_index = 0
    if not played.empty:
        kamp_count = {}
        for i, row in played.iterrows():
            h, a = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
            kamp_count[h] = kamp_count.get(h, 0) + 1; kamp_count[a] = kamp_count.get(a, 0) + 1
            if all(val >= 22 for val in kamp_count.values()): 
                cutoff_index = played.index.get_loc(i)
                break
            
    # Tabellen beregnes nu ALTID med alle 12 hold fra DEFAULT_SEASON og DEFAULT_COMP
    gs_df = beregn_tabel(played.iloc[:cutoff_index + 1], DEFAULT_SEASON, DEFAULT_COMP) if cutoff_index > 0 else beregn_tabel(played, DEFAULT_SEASON, DEFAULT_COMP)
    slut_df = beregn_tabel(played, DEFAULT_SEASON, DEFAULT_COMP)
    
    top6 = gs_df.head(6)['UUID'].tolist() if not gs_df.empty else []
    bund6 = gs_df.tail(6)['UUID'].tolist() if not gs_df.empty else []
    
    t_gs, t_slut, t_h2h = st.tabs(["Grundspil", "Slutspil", "Head-to-head"])
    
    with t_gs: 
        vis_tabel(gs_df, None)
        
    with t_slut:
        c1, c2 = st.columns(2)
        with c1: 
            st.subheader("Oprykningsspil")
            vis_tabel(slut_df, top6)
            render_kampe_dynamisk(played, top6)
        with c2: 
            st.subheader("Nedrykningsspil")
            vis_tabel(slut_df, bund6)
            render_kampe_dynamisk(played, bund6)
            
    with t_h2h:
        alle_hold = sorted(gs_df['HOLD'].tolist()) if not gs_df.empty else []
        if len(alle_hold) >= 2:
            c1, c2 = st.columns(2)
            default_hvidovre_idx = next((i for i, h in enumerate(alle_hold) if "hvidovre" in h.lower()), 0)
            
            t1 = c1.selectbox("Hold 1", alle_hold, index=default_hvidovre_idx)
            t2_options = [h for h in alle_hold if h != t1]
            t2 = c2.selectbox("Hold 2", t2_options, index=0)
            
            tabs = st.tabs(["Generelt", "xG Stats", "Afslutninger", "Defensivt", "Spilopbygning"])
            with tabs[0]: draw_h2h_chart(t1, t2, ['SHOTS', 'GOALS', 'MATCHTEMPO'], ['Skud', 'Mål', 'Tempo'], df_wy, "gen")
            with tabs[1]: draw_h2h_chart(t1, t2, ['XG', 'XGPERSHOT'], ['Total xG', 'xG pr. skud'], df_wy, "xg")
            with tabs[2]: draw_h2h_chart(t1, t2, ['SHOTSONTARGET', 'SHOTSBLOCKED', 'SHOTSFROMBOX', 'SHOTSFROMDANGERZONE'], ['På mål', 'Blokeret', 'I feltet', 'Danger Zone'], df_wy, "shot")
            with tabs[3]: draw_h2h_chart(t1, t2, ['INTERCEPTIONS', 'TACKLES', 'CLEARANCES'], ['Interc.', 'Tackler', 'Clearing'], df_wy, "def")
            with tabs[4]: draw_h2h_chart(t1, t2, ['PASSES', 'CROSSESTOTAL', 'PROGRESSIVEPASSES', 'PASSTOFINALTHIRDS'], ['Aflev.', 'Indlæg', 'Progr.', 'Sidste 1/3'], df_wy, "pass")

if __name__ == "__main__":
    st.markdown("<style>.league-table { width: 100%; border-collapse: collapse; }</style>", unsafe_allow_html=True)
    vis_side()
