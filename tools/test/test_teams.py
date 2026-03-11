import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS

# --- 1. GLOBALE HJÆLPEFUNKTIONER ---

def get_text_color(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (r * 0.299 + g * 0.587 + b * 0.114)
    return "black" if luminance > 165 else "white"

def draw_h2h_chart_wyscout(n1, n2, metrics, labels, per_match=True):
    dp = st.session_state.get("dp", {})
    df_wy = dp.get("wyscout", {}).get("team_stats_full", pd.DataFrame())
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    
    if df_wy.empty:
        st.warning("Wyscout data ikke tilgængelig.")
        return

    # Matcher holdnavne (Sørg for at 'Hvidovre' findes i begge)
    t1_data = df_wy[df_wy['TEAMNAME'].str.contains(n1, case=False, na=False)]
    t2_data = df_wy[df_wy['TEAMNAME'].str.contains(n2, case=False, na=False)]

    if t1_data.empty or t2_data.empty:
        st.info(f"Venter på Wyscout-match for {n1} vs {n2}...")
        return

    t1, t2 = t1_data.iloc[0], t2_data.iloc[0]

    def get_vals(data):
        m_count = data.get('MATCHES', 1) or 1
        return [data.get(m, 0) / m_count if per_match else data.get(m, 0) for m in metrics]

    y1, y2 = get_vals(t1), get_vals(t2)

    fig = go.Figure()
    c1 = colors_dict.get(n1, {"primary": "#cc0000"})
    c2 = colors_dict.get(n2, {"primary": "#0056a3"})

    for name, vals, color in [(n1, y1, c1), (n2, y2, color)]:
        fig.add_trace(go.Bar(
            name=name, x=labels, y=vals, 
            marker_color=color["primary"],
            text=[f"{v:.1f}" for v in vals],
            textposition='inside',
            insidetextfont=dict(size=14, color=get_text_color(color["primary"]), family="Arial Black")
        ))

    fig.update_layout(barmode='group', height=350, margin=dict(t=50, b=40, l=10, r=10),
                      plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- 2. HOVEDSIDE ---

def vis_side(df_raw=None):
    if "dp" not in st.session_state: return

    hif_rod = "#df003b"
    
    dp = st.session_state["dp"]
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    logo_map = dp.get("logo_map", {})
    df = dp.get("opta", {}).get("matches", pd.DataFrame())

    # --- HJÆLPEFUNKTIONER (DIN ORIGINALE STIL) ---
    def get_logo_url(opta_uuid, team_name):
        wy_id = next((info.get('team_wyid') for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
        return logo_map.get(wy_id, next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), ""))

    def get_logo_html(uuid):
        url = get_logo_url(uuid, "")
        return f'<img src="{url}" width="20">' if url else ""

    def update_form(current_form, result):
        return "".join((list(current_form) + [result])[-5:])

    def style_form(f):
        res = ""
        for char in f:
            color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
            res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
        return res

    # --- DATABEREGNING (LIGATABEL) ---
    stats = {}
    for _, row in df.iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid}

        if row['MATCH_STATUS'] == 'Played':
            h_g, a_g = int(row.get('TOTAL_HOME_SCORE', 0)), int(row.get('TOTAL_AWAY_SCORE', 0))
            winner = str(row.get('WINNER', '')).lower()
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            s_h['K'] += 1; s_a['K'] += 1; s_h['M+'] += h_g; s_h['M-'] += a_g; s_a['M+'] += a_g; s_a['M-'] += h_g
            if winner == 'home':
                s_h['V'] += 1; s_h['P'] += 3; s_h['FORM'] = update_form(s_h['FORM'], 'V'); s_a['T'] += 1; s_a['FORM'] = update_form(s_a['FORM'], 'T')
            elif winner == 'away':
                s_a['V'] += 1; s_a['P'] += 3; s_a['FORM'] = update_form(s_a['FORM'], 'V'); s_h['T'] += 1; s_h['FORM'] = update_form(s_h['FORM'], 'T')
            else:
                s_h['U'] += 1; s_h['P'] += 1; s_h['FORM'] = update_form(s_h['FORM'], 'U'); s_a['U'] += 1; s_a['P'] += 1; s_a['FORM'] = update_form(s_a['FORM'], 'U')

    # Næste modstander logik (Din originale)
    next_opp = {}
    df_up = df[df['MATCH_STATUS'] != 'Played'].copy()
    if not df_up.empty:
        df_up['MATCH_DATE_FULL'] = pd.to_datetime(df_up['MATCH_DATE_FULL'])
        df_up = df_up.sort_values('MATCH_DATE_FULL')
        for uuid in stats:
            m = df_up[(df_up['CONTESTANTHOME_OPTAUUID'] == uuid) | (df_up['CONTESTANTAWAY_OPTAUUID'] == uuid)]
            if not m.empty:
                r = m.iloc[0]
                is_h = r['CONTESTANTHOME_OPTAUUID'] == uuid
                opp_n = r['CONTESTANTAWAY_NAME'] if is_h else r['CONTESTANTHOME_NAME']
                opp_u = r['CONTESTANTAWAY_OPTAUUID'] if is_h else r['CONTESTANTHOME_OPTAUUID']
                next_opp[uuid] = f'<div style="display:flex;align-items:center;gap:5px;"><img src="{get_logo_url(opp_u, "")}" width="18"><span>{opp_n}</span></div>'

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga['NÆSTE'] = df_liga['UUID'].map(next_opp).fillna("-")
    df_liga = df_liga.sort_values(by=['P', 'MD'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- VISNING ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        st.markdown("""<style>.league-table { width: 100%; border-collapse: collapse; font-size: 14px; } 
                    .league-table td, .league-table th { padding: 8px; text-align: center; border-bottom: 1px solid #eee; }</style>""", unsafe_allow_html=True)
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        st.write(df_disp[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM', 'NÆSTE']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])
        
        st.subheader("Wyscout Advanced Stats (Per kamp)")
        tabs = st.tabs(["Angreb", "Forsvar", "Spilopbygning"])
        with tabs[0]: draw_h2h_chart_wyscout(team1, team2, ['XGSHOT', 'TOUCHINBOX'], ['Expected Goals', 'Berør. i felt'])
        with tabs[1]: draw_h2h_chart_wyscout(team1, team2, ['RECOVERIES', 'INTERCEPTIONS'], ['Genvindinger', 'Interceptions'])
        with tabs[2]: draw_h2h_chart_wyscout(team1, team2, ['PROGRESSIVERUN', 'SUCCESSFULDRIBBLES'], ['Prog. løb', 'Driblinger'])
