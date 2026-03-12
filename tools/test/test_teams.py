import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(df_raw=None):
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet.")
        return

    dp = st.session_state["dp"]
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    logo_map = dp.get("logo_map", {})
    df_opta = dp.get("opta", {}).get("matches", pd.DataFrame())
    
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"

    if df_opta.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # --- 1. HJÆLPEFUNKTIONER ---
    def get_logo_url(opta_uuid):
        wy_id = next((info.get('team_wyid') for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
        if wy_id and wy_id in logo_map:
            return logo_map[wy_id]
        return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

    def get_logo_html(uuid):
        url = get_logo_url(uuid)
        return f'<img src="{url}" width="20">' if url else ""

    def update_form(current_form, result):
        return "".join((list(current_form) + [result])[-5:])

    def style_form(f):
        res = ""
        for char in f:
            color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
            res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
        return res

    def get_text_color(hex_color):
        if not hex_color: return "white"
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (r * 0.299 + g * 0.587 + b * 0.114)
        return "black" if luminance > 165 else "white"

    # --- 2. DATABEREGNING (OPTA LIGATABEL) ---
    stats = {}
    for _, row in df_opta.iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid}
        
        if row['MATCH_STATUS'] == 'Played':
            h_g = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
            a_g = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
            winner = str(row['WINNER']).lower()
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            
            s_h['K'] += 1; s_a['K'] += 1
            s_h['M+'] += h_g; s_h['M-'] += a_g; s_a['M+'] += a_g; s_a['M-'] += h_g
            
            if winner == 'home':
                s_h['V'] += 1; s_h['P'] += 3; s_h['FORM'] = update_form(s_h['FORM'], 'V')
                s_a['T'] += 1; s_a['FORM'] = update_form(s_a['FORM'], 'T')
            elif winner == 'away':
                s_a['V'] += 1; s_a['P'] += 3; s_a['FORM'] = update_form(s_a['FORM'], 'V')
                s_h['T'] += 1; s_h['FORM'] = update_form(s_h['FORM'], 'T')
            else:
                s_h['U'] += 1; s_h['P'] += 1; s_h['FORM'] = update_form(s_h['FORM'], 'U')
                s_a['U'] += 1; s_a['P'] += 1; s_a['FORM'] = update_form(s_a['FORM'], 'U')

    next_opponents = {}
    df_upcoming = df_opta[df_opta['MATCH_STATUS'] != 'Played'].copy()
    if not df_upcoming.empty:
        df_upcoming['MATCH_DATE_FULL'] = pd.to_datetime(df_upcoming['MATCH_DATE_FULL'])
        df_upcoming = df_upcoming.sort_values('MATCH_DATE_FULL')
        for uuid in stats.keys():
            future_m = df_upcoming[(df_upcoming['CONTESTANTHOME_OPTAUUID'] == uuid) | (df_upcoming['CONTESTANTAWAY_OPTAUUID'] == uuid)]
            if not future_m.empty:
                r = future_m.iloc[0]
                is_h = r['CONTESTANTHOME_OPTAUUID'] == uuid
                opp_n = r['CONTESTANTAWAY_NAME'] if is_h else r['CONTESTANTHOME_NAME']
                opp_u = r['CONTESTANTAWAY_OPTAUUID'] if is_h else r['CONTESTANTHOME_OPTAUUID']
                dato = r['MATCH_DATE_FULL'].strftime('%d/%m')
                logo = get_logo_url(opp_u)
                next_opponents[uuid] = f'<div style="display:flex;align-items:center;gap:5px;"><img src="{logo}" width="18"><span>{opp_n}</span><span style="color:#888;font-size:11px;">{dato}</span></div>'

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga['NÆSTE'] = df_liga['UUID'].map(next_opponents).fillna("-")
    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- 3. WYSCOUT DATA ---
    @st.cache_data(ttl=600)
    def get_wyscout_direct():
        if not conn: return pd.DataFrame()
        query = f"""
        SELECT t.TEAMNAME, 
               adv.XG, adv.SHOTS, adv.GOALS, adv.XGPERSHOT, 
               adv.AVGDISTANCE, adv.SHOTSONTARGET, adv.SHOTSBLOCKED, 
               adv.SHOTSOUTSIDEBOX, adv.SHOTSFROMBOX, adv.SHOTSFROMBOXONTARGET, 
               adv.SHOTSFROMDANGERZONE,
               md.INTERCEPTIONS, md.TACKLES, md.CLEARANCES, md.PPDA,
               mp.PASSES, mp.PASSESSUCCESSFUL, mp.CROSSESTOTAL, mp.FORWARDPASSES, 
               mp.PROGRESSIVEPASSES, mp.PASSTOFINALTHIRDS, mp.AVGPASSLENGTH, mp.MATCHTEMPO
        FROM {DB}.WYSCOUT_TEAMMATCHES tm 
        JOIN {DB}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328
        """
        return conn.query(query)

    df_wy_raw = get_wyscout_direct()
    
    def draw_h2h_chart_combined(team1, team2, metrics, labels, df_source, chart_key):
        d1 = df_source[df_source['TEAMNAME'].str.contains(team1, case=False, na=False)]
        d2 = df_source[df_source['TEAMNAME'].str.contains(team2, case=False, na=False)]
        
        if d1.empty or d2.empty:
            st.info("Ingen data fundet.")
            return

        # Definer x_indices med det samme baseret på labels
        x_indices = list(range(len(labels)))
        v1 = [d1.iloc[0].get(m, 0) for m in metrics]
        v2 = [d2.iloc[0].get(m, 0) for m in metrics]
        
        # Logo URL logik
        u1 = df_liga[df_liga['HOLD'] == team1]['UUID'].values[0] if team1 in df_liga['HOLD'].values else None
        u2 = df_liga[df_liga['HOLD'] == team2]['UUID'].values[0] if team2 in df_liga['HOLD'].values else None
        l1, l2 = get_logo_url(u1), get_logo_url(u2)
        
        # Farve logik
        c1 = colors_dict.get(team1, {"primary": "#df003b", "secondary": "#df003b"})
        c2 = colors_dict.get(team2, {"primary": "#0056a3", "secondary": "#0056a3"})

        def is_white(color):
            c = str(color).lower().strip()
            return c in ['#ffffff', 'white', '#fff', '#fcfcfc']

        h1_line_color = c1.get("secondary", c1["primary"]) if is_white(c1["primary"]) else c1["primary"]
        h1_line_width = 2 if is_white(c1["primary"]) else 0
        h2_line_color = c2.get("secondary", c2["primary"]) if is_white(c2["primary"]) else c2["primary"]
        h2_line_width = 2 if is_white(c2["primary"]) else 0

        fig = go.Figure()
        
        # Tilføj Bar traces
        fig.add_trace(go.Bar(
            name=team1, x=x_indices, y=v1, 
            marker_color=c1["primary"], 
            marker_line_color=h1_line_color, marker_line_width=h1_line_width,
            text=[f"{x:.2f}" for x in v1], textposition='inside', 
            insidetextfont=dict(size=14, family="Arial", color=get_text_color(c1["primary"])),
            offsetgroup=1
        ))
        
        fig.add_trace(go.Bar(
            name=team2, x=x_indices, y=v2, 
            marker_color=c2["primary"], 
            marker_line_color=h2_line_color, marker_line_width=h2_line_width,
            text=[f"{x:.2f}" for x in v2], textposition='inside', 
            insidetextfont=dict(size=12, family="Arial", color=get_text_color(c2["primary"])),
            offsetgroup=2
        ))

        # Logo løkke (bruger nu x_indices korrekt)
        for i in x_indices:
            if l1:
                fig.add_layout_image(dict(
                    source=l1, xref="x", yref="paper",
                    x=i - 0.20, y=1.05, sizex=0.18, sizey=0.18,
                    xanchor="center", yanchor="bottom", opacity=1, layer="above"
                ))
            if l2:
                fig.add_layout_image(dict(
                    source=l2, xref="x", yref="paper",
                    x=i + 0.20, y=1.05, sizex=0.18, sizey=0.18,
                    xanchor="center", yanchor="bottom", opacity=1, layer="above"
                ))

        fig.update_layout(
            barmode='group',
            bargap=0.30,
            bargroupgap=0.12, # Mellemrum mellem de to hold
            height=500,
            margin=dict(t=100, b=150, l=20, r=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            yaxis=dict(visible=False, fixedrange=True, range=[0, max(max(v1 or [0]), max(v2 or [0])) * 1.4]),
            xaxis=dict(
                type='category', showgrid=False, tickmode='array', tickvals=x_indices, ticktext=labels,
                tickfont=dict(size=16, family="Arial", color="#333333"), 
                tickangle=0, automargin=True, fixedrange=True, anchor="y", side="bottom"
            )
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=chart_key)

    # --- 5. LAYOUT ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        st.markdown("""<style>
            .league-table { width: 100%; border-collapse: collapse; font-size: 14px; }
            .league-table th { background-color: rgba(128,128,128,0.1); padding: 8px; text-align: center !important; }
            .league-table td { padding: 8px; border-bottom: 1px solid rgba(128,128,128,0.2); text-align: center !important; }
            .league-table td:nth-child(3) { text-align: left !important; font-weight: bold; }
        </style>""", unsafe_allow_html=True)
        
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        
        st.write(df_disp[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM', 'NÆSTE']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)
        
    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        if not df_wy_raw.empty:
            df_wy_raw.columns = [col.upper() for col in df_wy_raw.columns]
            df_agg = df_wy_raw.groupby('TEAMNAME').mean(numeric_only=True).reset_index()
            
            sub_tabs = st.tabs(["Generelt", "xG Stats", "Afslutninger", "Defensivt", "Spilopbygning"])
            
            with sub_tabs[0]:
                draw_h2h_chart_combined(team1, team2, ['SHOTS', 'GOALS', 'PPDA', 'MATCHTEMPO'], ['Skud', 'Mål', 'PPDA', 'Tempo'], df_agg, "gen_chart")
            with sub_tabs[1]:
                draw_h2h_chart_combined(team1, team2, ['XG', 'XGPERSHOT'], ['Total xG', 'xG pr. skud'], df_agg, "xg_chart")
            with sub_tabs[2]:
                draw_h2h_chart_combined(team1, team2, ['SHOTSONTARGET', 'SHOTSBLOCKED', 'SHOTSOUTSIDEBOX', 'SHOTSFROMBOX', 'SHOTSFROMBOXONTARGET', 'SHOTSFROMDANGERZONE'], ['På mål', 'Blokeret', 'Udenfor felt', 'I feltet', 'I felt på mål', 'Danger Zone'], df_agg, "shot_chart")
            with sub_tabs[3]:
                draw_h2h_chart_combined(team1, team2, ['INTERCEPTIONS', 'TACKLES', 'CLEARANCES'], ['Interceptions', 'Tacklinger', 'Clearinger'], df_agg, "def_chart")
            with sub_tabs[4]:
                draw_h2h_chart_combined(team1, team2, ['PASSES', 'CROSSESTOTAL', 'FORWARDPASSES', 'PROGRESSIVEPASSES', 'PASSTOFINALTHIRDS'], ['Afleveringer', 'Indlæg', 'Fremadrettede', 'Progressive', 'Til sidste 1/3'], df_agg, "pass_chart")
