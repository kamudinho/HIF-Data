import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- 1. GLOBALE HJÆLPEFUNKTIONER (Uden for vis_side) ---

def get_text_color(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (r * 0.299 + g * 0.587 + b * 0.114)
    return "black" if luminance > 165 else "white"

def draw_h2h_chart_wyscout(n1, n2, metrics, labels, per_match=True):
    """Tegner sammenligning baseret på Wyscout team_stats_full."""
    dp = st.session_state.get("dp", {})
    df_wy = dp.get("wyscout", {}).get("team_stats_full", pd.DataFrame())
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    
    if df_wy.empty:
        st.warning("Wyscout team data ikke tilgængelig.")
        return

    # Tjek om holdene findes i Wyscout datasættet
    if n1 not in df_wy['TEAMNAME'].values or n2 not in df_wy['TEAMNAME'].values:
        st.error(f"Kunne ikke finde data for {n1} eller {n2} i Wyscout.")
        return

    t1_data = df_wy[df_wy['TEAMNAME'] == n1].iloc[0]
    t2_data = df_wy[df_wy['TEAMNAME'] == n2].iloc[0]

    # Beregn værdier (Normaliser til 'per kamp' hvis valgt)
    def calc_vals(data):
        vals = []
        # Vi bruger appearances/matches fra Wyscout dataen selv
        matches = data.get('MATCHES', 1) 
        if matches == 0: matches = 1
        for m in metrics:
            val = data.get(m, 0)
            vals.append(val / matches if per_match else val)
        return vals

    y1_vals = calc_vals(t1_data)
    y2_vals = calc_vals(t2_data)

    fig = go.Figure()
    c1 = colors_dict.get(n1, {"primary": "#cc0000"})
    c2 = colors_dict.get(n2, {"primary": "#0056a3"})

    bar_width = 0.35
    
    # Hold 1 Bar
    fig.add_trace(go.Bar(
        name=n1, x=labels, y=y1_vals, 
        marker_color=c1["primary"],
        text=[f"{v:.1f}" if per_match else int(v) for v in y1_vals],
        textposition='inside', width=bar_width,
        insidetextfont=dict(size=14, color=get_text_color(c1["primary"]), family="Arial Black")
    ))

    # Hold 2 Bar
    fig.add_trace(go.Bar(
        name=n2, x=labels, y=y2_vals, 
        marker_color=c2["primary"],
        text=[f"{v:.1f}" if per_match else int(v) for v in y2_vals],
        textposition='inside', width=bar_width,
        insidetextfont=dict(size=14, color=get_text_color(c2["primary"]), family="Arial Black")
    ))

    # Tilføj logoer over hver bar-gruppe
    for i in range(len(labels)):
        logo1 = next((info['logo'] for name, info in TEAMS.items() if name == n1), "")
        logo2 = next((info['logo'] for name, info in TEAMS.items() if name == n2), "")
        if logo1:
            fig.add_layout_image(dict(source=logo1, xref="x", yref="paper", x=i-0.18, y=1.1, sizex=0.12, sizey=0.12, xanchor="center", yanchor="middle"))
        if logo2:
            fig.add_layout_image(dict(source=logo2, xref="x", yref="paper", x=i+0.18, y=1.1, sizex=0.12, sizey=0.12, xanchor="center", yanchor="middle"))

    fig.update_layout(
        barmode='group', height=400, margin=dict(t=100, b=40, l=10, r=10),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False,
        yaxis=dict(visible=False, fixedrange=True, range=[0, max(max(y1_vals), max(y2_vals)) * 1.3]),
        xaxis=dict(fixedrange=True, tickfont=dict(size=12, family="Arial Black"))
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})


# --- 2. HOVEDSIDE ---

def vis_side(df_raw=None):
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet.")
        return

    dp = st.session_state["dp"]
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    logo_map = dp.get("logo_map", {})
    df_opta = dp.get("opta", {}).get("matches", pd.DataFrame())

    if df_opta.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # --- HJÆLPEFUNKTIONER TIL TABEL ---
    def get_logo_url(opta_uuid, team_name):
        wy_id = next((info.get('team_wyid') for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
        if wy_id and wy_id in logo_map:
            return logo_map[wy_id]
        return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

    def get_logo_html(uuid):
        url = get_logo_url(uuid, "")
        return f'<img src="{url}" width="20">' if url else ""

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

    # --- DATABEREGNING (OPTA TABEL) ---
    stats = {}
    for _, row in df_opta.iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        h_g = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_g = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
        winner = str(row['WINNER']).lower()

        for uuid, name in [(h_uuid, h_name), (a_uuid, a_name)]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid}

        if row['MATCH_STATUS'] == 'Played':
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            s_h['K'] += 1; s_a['K'] += 1
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

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- LAYOUT ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head (Wyscout)"])

    with t_liga:
        st.markdown("""<style>.league-table { width: 100%; font-size: 14px; border-collapse: collapse; } 
                    .league-table td, .league-table th { padding: 8px; text-align: center; border-bottom: 1px solid #eee; }</style>""", unsafe_allow_html=True)
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        st.write(df_disp[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_h2h:
        # Brug navne fra Wyscout for at sikre match
        df_wy = dp.get("wyscout", {}).get("team_stats_full", pd.DataFrame())
        if not df_wy.empty:
            h_list = sorted(df_wy['TEAMNAME'].unique())
            c1, c2 = st.columns(2)
            team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
            team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

            w_tabs = st.tabs(["🔥 Offensivt", "🛡️ Defensivt", "🎯 Præcision"])
            
            with w_tabs[0]:
                # Metrics fra din 'player_stats_total' query aggregeret på hold
                draw_h2h_chart_wyscout(team1, team2, ['XGSHOT', 'PROGRESSIVERUN', 'TOUCHINBOX'], ['xG', 'Prog. Løb', 'Felt-berør.'])
            
            with w_tabs[1]:
                draw_h2h_chart_wyscout(team1, team2, ['RECOVERIES', 'INTERCEPTIONS', 'DUELSWON'], ['Genvindinger', 'Interceptions', 'Dueller Vundet'])
            
            with w_tabs[2]:
                draw_h2h_chart_wyscout(team1, team2, ['SUCCESSFULPASSES', 'KEYPASSES', 'SUCCESSFULDRIBBLES'], ['Aflev. OK', 'Key Passes', 'Driblinger OK'])
        else:
            st.warning("Ingen Wyscout data fundet til Head-to-head.")
