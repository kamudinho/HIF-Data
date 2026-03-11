import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS

def vis_side(df_raw=None):
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet.")
        return

    dp = st.session_state["dp"]
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    logo_map = dp.get("logo_map", {})
    df = dp.get("opta", {}).get("matches", pd.DataFrame())

    if df.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # --- 1. HJÆLPEFUNKTIONER ---
    def get_logo_url(opta_uuid, team_name):
        wy_id = next((info.get('wyid') for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
        if wy_id and wy_id in logo_map:
            return logo_map[wy_id]
        return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

    def get_logo_html(uuid):
        url = get_logo_url(uuid, "")
        return f'<img src="{url}" width="20">' if url else ""

    def get_text_color(hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (r * 0.299 + g * 0.587 + b * 0.114)
        return "black" if luminance > 165 else "white"

    def update_form(current_form, result):
        form_list = list(current_form)
        form_list.append(result)
        return "".join(form_list[-5:])

    def style_form(f):
        res = ""
        for char in f:
            color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
            res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
        return res

    # --- 2. DATABEREGNING ---
    stats = {}
    for _, row in df.iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        h_g = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_g = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
        winner = str(row['WINNER']).lower()

        for uuid, name in [(h_uuid, h_name), (a_uuid, a_name)]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid, 'MATCHES': 0}

        if row['MATCH_STATUS'] == 'Played':
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            s_h['K'] += 1; s_a['K'] += 1
            s_h['MATCHES'] += 1; s_a['MATCHES'] += 1
            s_h['M+'] += h_g; s_h['M-'] += a_g
            s_a['M+'] += a_g; s_a['M-'] += h_g

            if winner == 'home':
                s_h['V'] += 1; s_h['P'] += 3; s_h['FORM'] = update_form(s_h['FORM'], 'V')
                s_a['T'] += 1; s_a['FORM'] = update_form(s_a['FORM'], 'T')
            elif winner == 'away':
                s_a['V'] += 1; s_a['P'] += 3; s_a['FORM'] = update_form(s_a['FORM'], 'V')
                s_h['T'] += 1; s_h['FORM'] = update_form(s_h['FORM'], 'T')
            else:
                s_h['U'] += 1; s_h['P'] += 1; s_h['FORM'] = update_form(s_h['FORM'], 'U')
                s_a['U'] += 1; s_a['P'] += 1; s_a['FORM'] = update_form(s_a['FORM'], 'U')

    # Find næste modstander
    next_opponents = {}
    df_upcoming = df[df['MATCH_STATUS'] != 'Played'].copy()
    if not df_upcoming.empty:
        df_upcoming['MATCH_DATE_FULL'] = pd.to_datetime(df_upcoming['MATCH_DATE_FULL'])
        df_upcoming = df_upcoming.sort_values('MATCH_DATE_FULL', ascending=True)

    for uuid in stats.keys():
        future_m = df_upcoming[(df_upcoming['CONTESTANTHOME_OPTAUUID'] == uuid) | 
                                (df_upcoming['CONTESTANTAWAY_OPTAUUID'] == uuid)]

        if not future_m.empty:
            row = future_m.iloc[0]
            is_home = row['CONTESTANTHOME_OPTAUUID'] == uuid
            opp_name = row['CONTESTANTAWAY_NAME'] if is_home else row['CONTESTANTHOME_NAME']
            opp_uuid = row['CONTESTANTAWAY_OPTAUUID'] if is_home else row['CONTESTANTHOME_OPTAUUID']

            dato = row['MATCH_DATE_FULL'].strftime('%d/%m')
            logo = get_logo_url(opp_uuid, opp_name)

            html_content = f'<div style="display:flex;align-items:center;gap:5px;"><img src="{logo}" width="18"><span>{opp_name}</span><span style="color:#888;font-size:11px;">{dato}</span></div>'
            next_opponents[uuid] = html_content
        else:
            next_opponents[uuid] = "-"

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga['NÆSTE'] = df_liga['UUID'].map(next_opponents)

    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- 3. GRAF FUNKTION ---
    def draw_h2h_chart_wyscout(n1, n2, metrics, labels):
    # 1. Hent Wyscout-data fra session_state (fra din get_wy_queries)
        df_wy = st.session_state["dp"].get("wyscout", {}).get("team_stats_full", pd.DataFrame())
        
        if df_wy.empty:
            st.warning("Wyscout team data ikke tilgængelig.")
            return
    
        # 2. Filtrer for de to valgte hold
        t1_data = df_wy[df_wy['TEAMNAME'] == n1].iloc[0]
        t2_data = df_wy[df_wy['TEAMNAME'] == n2].iloc[0]
    
        # 3. Forbered værdier (Eksempel: Progressive Runs, Dribbles, etc.)
        # Vi bruger 'MATCHES' fra din Opta-tabel til at få 'Per kamp' stats
        y1_vals = [t1_data[m] / t1_data['MATCHES'] if 'MATCHES' in t1_data else t1_data[m] for m in metrics]
        y2_vals = [t2_data[m] / t2_data['MATCHES'] if 'MATCHES' in t2_data else t2_data[m] for m in metrics]

        c1 = colors_dict.get(n1, {"primary": "#cc0000"})
        c2 = colors_dict.get(n2, {"primary": "#0056a3"})

        bar_width = 0.25
        for i, trace in enumerate([(n1, y1_vals, c1), (n2, y2_vals, c2)]):
            fig.add_trace(go.Bar(
                name=trace[0], x=labels, y=trace[1], 
                marker_color=trace[2]["primary"],
                text=[f"{v:.1f}" if per_match else int(v) for v in trace[1]], 
                textposition='inside', width=bar_width,
                insidetextfont=dict(size=16, color=get_text_color(trace[2]["primary"]), family="Arial Black")
            ))

        for i in range(len(labels)):
            url1 = logo_map.get(n1) or get_logo_url(t1['UUID'], n1)
            url2 = logo_map.get(n2) or get_logo_url(t2['UUID'], n2)
            if url1:
                fig.add_layout_image(dict(source=url1, xref="x", yref="paper", x=i-0.20, y=1.15, sizex=0.10, sizey=0.10, xanchor="center", yanchor="middle"))
            if url2:
                fig.add_layout_image(dict(source=url2, xref="x", yref="paper", x=i+0.20, y=1.15, sizex=0.10, sizey=0.10, xanchor="center", yanchor="middle"))

        fig.update_layout(
            barmode='group', bargap=0.25, height=450, margin=dict(t=110, b=40, l=10, r=10),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False,
            yaxis=dict(visible=False, fixedrange=True, range=[0, max(max(y1_vals), max(y2_vals)) * 1.2]),
            xaxis=dict(fixedrange=True, tickfont=dict(size=14, family="Arial Black"))
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 4. LAYOUT ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        st.markdown("""
            <style>
                .league-table { width: 100%; border-collapse: collapse; font-size: 14px; }
                .league-table th { text-align: center !important; padding: 8px; border-bottom: 2px solid #eee; background-color: rgba(0,0,0,0.03); }
                .league-table td { text-align: center !important; padding: 8px; border-bottom: 1px solid #eee; }
                .league-table td:nth-child(1), .league-table th:nth-child(1) { text-align: center !important; width: 30px; font-weight: bold; }
                .league-table td:nth-child(2) { width: 40px; }
                .league-table td:nth-child(3), .league-table th:nth-child(3) { text-align: left !important; font-weight: bold; }
            </style>
        """, unsafe_allow_html=True)

        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)

        vis_cols = ['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM', 'NÆSTE']
        st.write(df_disp[vis_cols].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Vælg Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Vælg Hold 2", [h for h in h_list if h != team1])

        sub_tabs = st.tabs(["Generelt", "Offensivt", "Defensivt"])
        with sub_tabs[0]: draw_h2h_chart(team1, team2, ['P', 'V', 'K'], ['Point', 'Sejre', 'Kampe'])
        with sub_tabs[1]: draw_h2h_chart(team1, team2, ['M+'], ['Mål Scoret'])
        with sub_tabs[2]: draw_h2h_chart(team1, team2, ['M-'], ['Mål Imod'])
