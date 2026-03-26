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
    return pd.read_sql(query, conn)

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
    return pd.read_sql(query, conn)

# --- 3. CHART FUNKTION (HEAD-TO-HEAD) ---

def draw_h2h_chart(team1, team2, metrics, labels, df_wy, chart_key, df_liga):
    fig = go.Figure()
    col_width = 0.18
    gap = 0.05

    u1 = df_liga[df_liga['HOLD'] == team1]['UUID'].values[0]
    u2 = df_liga[df_liga['HOLD'] == team2]['UUID'].values[0]
    l1, l2 = get_logo_url(u1), get_logo_url(u2)

    for i, m in enumerate(metrics):
        suffix = f"{i+1}" if i > 0 else ""
        xref, yref = f"x{suffix}", f"y{suffix}"
        
        d1 = df_wy[df_wy['TEAMNAME'].str.contains(team1, case=False, na=False)]
        d2 = df_wy[df_wy['TEAMNAME'].str.contains(team2, case=False, na=False)]
        v1 = float(d1[m.upper()].iloc[0] if not d1.empty else 0)
        v2 = float(d2[m.upper()].iloc[0] if not d2.empty else 0)
        
        prec = ".2f" if 'XG' in m.upper() else ".1f"
        max_y = max(v1, v2, 0.5)

        # 1. Søjler
        fig.add_trace(go.Bar(
            x=[0, 1], y=[v1, v2],
            marker_color=[TEAM_COLORS.get(team1, {}).get("primary", "#df003b"), 
                          TEAM_COLORS.get(team2, {}).get("primary", "#0056a3")],
            width=0.7, showlegend=False, xaxis=xref, yaxis=yref
        ))

        # 2. VÆRDIER OVER BARENE (Hvid skrift)
        fig.add_annotation(dict(
            x=0, y=v1, xref=xref, yref=yref, text=f"<b>{format(v1, prec)}</b>",
            showarrow=False, yshift=15, font=dict(size=13, color="black")
        ))
        fig.add_annotation(dict(
            x=1, y=v2, xref=xref, yref=yref, text=f"<b>{format(v2, prec)}</b>",
            showarrow=False, yshift=15, font=dict(size=13, color="black")
        ))

        # 3. KATEGORI UNDER BARENE
        fig.add_annotation(dict(
            x=0.5, y=-0.1, xref=f"{xref} domain", yref=f"{yref} domain",
            text=f"<b>{labels[i]}</b>", showarrow=False, 
            font=dict(size=12, color="black"), yanchor="top"
        ))

        # 4. LOGOER I TOPPEN
        if l1:
            fig.add_layout_image(dict(
                source=l1, xref=xref, yref="paper", x=0, y=1.05,
                sizex=0.25, sizey=0.25, xanchor="center", yanchor="bottom"
            ))
        if l2:
            fig.add_layout_image(dict(
                source=l2, xref=xref, yref="paper", x=1, y=1.05,
                sizex=0.25, sizey=0.25, xanchor="center", yanchor="bottom"
            ))

        # 5. AKSE SETUP
        fig.update_layout({
            f"xaxis{suffix}": dict(
                domain=[i*(col_width+gap), i*(col_width+gap)+col_width], 
                range=[-0.8, 1.8], showticklabels=False
            ),
            f"yaxis{suffix}": dict(range=[0, max_y * 1.8], visible=False)
        })

    fig.update_layout(
        height=380,
        margin=dict(t=50, b=80, l=20, r=20),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=chart_key)

# --- 4. HOVEDFUNKTION ---

def vis_side(dp_unused=None):
    df_opta = load_liga_data()
    df_wy = get_wyscout_stats()
    
    if df_opta.empty:
        st.warning("Data ikke fundet."); return

    df_opta.columns = [c.upper() for c in df_opta.columns]
    df_opta['MATCH_DATE_FULL'] = pd.to_datetime(df_opta['MATCH_DATE_FULL'])
    
    # Beregn Tabel-data
    stats = {}
    for _, row in df_opta.sort_values('MATCH_DATE_FULL').iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid}
        
        if str(row['MATCH_STATUS']).strip().capitalize() == 'Played':
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

    # Næste modstander
    next_opp = {}
    df_future = df_opta[df_opta['MATCH_STATUS'].str.strip().str.capitalize() != 'Played'].sort_values('MATCH_DATE_FULL')
    for uuid in stats.keys():
        f = df_future[(df_future['CONTESTANTHOME_OPTAUUID'] == uuid) | (df_future['CONTESTANTAWAY_OPTAUUID'] == uuid)]
        if not f.empty:
            r = f.iloc[0]
            is_h = r['CONTESTANTHOME_OPTAUUID'] == uuid
            opp_u = r['CONTESTANTAWAY_OPTAUUID'] if is_h else r['CONTESTANTHOME_OPTAUUID']
            opp_n = r['CONTESTANTAWAY_NAME'] if is_h else r['CONTESTANTHOME_NAME']
            dato = r['MATCH_DATE_FULL'].strftime('%d/%m')
            next_opp[uuid] = f'<div style="display:flex;align-items:center;gap:5px;"><img src="{get_logo_url(opp_u)}" width="18"><span>{opp_n}</span><span style="color:#888;font-size:10px;">{dato}</span></div>'

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga['NÆSTE'] = df_liga['UUID'].map(next_opp).fillna("-")
    df_liga = df_liga.sort_values(['P', 'MD'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        st.markdown("""
            <style>
                /* Generel tabel styling */
                .league-table { 
                    width: 100%; 
                    border-collapse: collapse; 
                    font-size: 14px; 
                } 
                
                /* 1. Centrer alle celler som udgangspunkt */
                .league-table th, .league-table td { 
                    text-align: center !important; 
                    padding: 8px 4px;
                    width: 90px;
                }

                /* 2. Venstrestil kolonne 3 (HOLD) */
                .league-table td:nth-child(3), 
                .league-table th:nth-child(3) { 
                    text-align: left !important; 
                    font-weight: bold;
                    width: 200px;
                }

                /* 3. Venstrestil kolonne 11 (NÆSTE) */
                .league-table td:nth-child(11), 
                .league-table th:nth-child(11) { 
                    text-align: left !important;
                    width: 350px;
                }

                /* Logo-kolonnen (nr. 2) skal ofte have lidt mindre bredde */
                .league-table td:nth-child(2) {
                    width: 30px !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        df_disp = df_liga.copy()
        # Sikr at vi har de rigtige kolonner til rådighed
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        
        # Hvis style_form returnerer HTML cirkler, så sørg for at de er centreret
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        
        # Vis tabellen
        st.write(df_disp[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM', 'NÆSTE']].to_html(
            escape=False, index=False, border=0, classes='league-table'), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        idx1 = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
        team1 = c1.selectbox("Hold 1", h_list, index=idx1)
        h_list2 = [h for h in h_list if h != team1]
        team2 = c2.selectbox("Hold 2", h_list2, index=0)

        # FANER TIL STATISTIK
        tabs = st.tabs(["Generelt", "xG Stats", "Afslutninger", "Defensivt", "Spilopbygning"])
        with tabs[0]: draw_h2h_chart(team1, team2, ['SHOTS', 'GOALS', 'PPDA', 'MATCHTEMPO'], ['Skud', 'Mål', 'PPDA', 'Tempo'], df_wy, "gen", df_liga)
        with tabs[1]: draw_h2h_chart(team1, team2, ['XG', 'XGPERSHOT'], ['Total xG', 'xG pr. skud'], df_wy, "xg", df_liga)
        with tabs[2]: draw_h2h_chart(team1, team2, ['SHOTSONTARGET', 'SHOTSBLOCKED', 'SHOTSFROMBOX', 'SHOTSFROMDANGERZONE'], ['På mål', 'Blokeret', 'I feltet', 'Danger Zone'], df_wy, "shot", df_liga)
        with tabs[3]: draw_h2h_chart(team1, team2, ['INTERCEPTIONS', 'TACKLES', 'CLEARANCES'], ['Interc.', 'Tackler', 'Clearing'], df_wy, "def", df_liga)
        with tabs[4]: draw_h2h_chart(team1, team2, ['PASSES', 'CROSSESTOTAL', 'PROGRESSIVEPASSES', 'PASSTOFINALTHIRDS'], ['Aflev.', 'Indlæg', 'Progr.', 'Sidste 1/3'], df_wy, "pass", df_liga)
