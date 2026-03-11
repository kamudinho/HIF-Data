import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import base64
import requests
from io import BytesIO
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. GLOBALE HJÆLPEFUNKTIONER (Uden for vis_side for bedre caching) ---
@st.cache_data(ttl=3600)
def get_base64_logo(url):
    """Henter billede og konverterer til base64 streng."""
    if not url or not url.startswith('http'):
        return url
    try:
        response = requests.get(url, timeout=5)
        img = BytesIO(response.content)
        return f"data:image/png;base64,{base64.b64encode(img.getvalue()).decode()}"
    except Exception:
        return url

def get_logo_url(opta_uuid, logo_map):
    wy_id = next((info.get('team_wyid') for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
    if wy_id and wy_id in logo_map:
        return logo_map[wy_id]
    return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

def get_text_color(hex_color):
    if not hex_color: return "white"
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (r * 0.299 + g * 0.587 + b * 0.114)
    return "black" if luminance > 165 else "white"

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

    # --- 2. DATABEREGNING ---
    stats = {}
    for _, row in df_opta.iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid, 'MATCHES': 0}
        
        if row['MATCH_STATUS'] == 'Played':
            h_g = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
            a_g = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
            winner = str(row['WINNER']).lower()
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            s_h['K'] += 1; s_a['K'] += 1; s_h['MATCHES'] += 1; s_a['MATCHES'] += 1
            s_h['M+'] += h_g; s_h['M-'] += a_g; s_a['M+'] += a_g; s_a['M-'] += h_g
            if winner == 'home':
                s_h['V'] += 1; s_h['P'] += 3; s_h['FORM'] = "".join((list(s_h['FORM']) + ['V'])[-5:])
                s_a['T'] += 1; s_a['FORM'] = "".join((list(s_a['FORM']) + ['T'])[-5:])
            elif winner == 'away':
                s_a['V'] += 1; s_a['P'] += 3; s_a['FORM'] = "".join((list(s_a['FORM']) + ['V'])[-5:])
                s_h['T'] += 1; s_h['FORM'] = "".join((list(s_h['FORM']) + ['T'])[-5:])
            else:
                s_h['U'] += 1; s_h['P'] += 1; s_h['FORM'] = "".join((list(s_h['FORM']) + ['U'])[-5:])
                s_a['U'] += 1; s_a['P'] += 1; s_a['FORM'] = "".join((list(s_a['FORM']) + ['U'])[-5:])

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- 3. WYSCOUT DATA ---
    @st.cache_data(ttl=600)
    def get_wyscout_direct():
        if not conn: return pd.DataFrame()
        query = f"""
        SELECT t.TEAMNAME, adv.XG, adv.SHOTS, md.INTERCEPTIONS, mp.PASSES
        FROM {DB}.WYSCOUT_TEAMMATCHES tm
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID
        JOIN {DB}.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
        JOIN {DB}.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
        JOIN {DB}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID
        WHERE tm.COMPETITION_WYID = 328 AND s.SEASONNAME LIKE '2025%2026'
        """
        return conn.query(query)

    df_wy_raw = get_wyscout_direct()

    # --- 4. GRAF FUNKTION (LOGOER OVER GRAFEN) ---
    def draw_h2h_chart_combined(team1, team2, metrics, labels, df_source):
        d1 = df_source[df_source['TEAMNAME'].str.contains(team1, case=False, na=False)]
        d2 = df_source[df_source['TEAMNAME'].str.contains(team2, case=False, na=False)]
        
        if d1.empty or d2.empty:
            st.info("Ingen data fundet for de valgte hold.")
            return

        v1 = [d1.iloc[0].get(m, 0) for m in metrics]
        v2 = [d2.iloc[0].get(m, 0) for m in metrics]
        
        u1 = df_liga[df_liga['HOLD'] == team1]['UUID'].values[0]
        u2 = df_liga[df_liga['HOLD'] == team2]['UUID'].values[0]
        
        l1 = get_base64_logo(get_logo_url(u1, logo_map))
        l2 = get_base64_logo(get_logo_url(u2, logo_map))
        
        c1 = colors_dict.get(team1, {"primary": "#df003b"})
        c2 = colors_dict.get(team2, {"primary": "#0056a3"})

        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name=team1, x=labels, y=v1, 
            marker_color=c1["primary"], 
            text=[f"{x:.2f}" for x in v1], 
            textposition='inside', 
            insidetextfont=dict(size=14, family="Arial Black", color=get_text_color(c1["primary"])),
            offsetgroup=1
        ))
        
        fig.add_trace(go.Bar(
            name=team2, x=labels, y=v2, 
            marker_color=c2["primary"], 
            text=[f"{x:.2f}" for x in v2], 
            textposition='inside', 
            insidetextfont=dict(size=14, family="Arial Black", color=get_text_color(c2["primary"])),
            offsetgroup=2
        ))

        # LOGOER PLACERET OVER GRAFEN (yref="paper")
        for i in range(len(labels)):
            if l1:
                fig.add_layout_image(dict(
                    source=l1, xref="x", yref="paper",
                    x=i, y=1.05, sizex=0.12, sizey=0.12,
                    xanchor="right", yanchor="bottom", opacity=1, layer="above"
                ))
            if l2:
                fig.add_layout_image(dict(
                    source=l2, xref="x", yref="paper",
                    x=i, y=1.05, sizex=0.12, sizey=0.12,
                    xanchor="left", yanchor="bottom", opacity=1, layer="above"
                ))

        fig.update_layout(
            barmode='group', height=450, 
            margin=dict(t=100, b=40, l=10, r=10), # Mere top-margin til logoer
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            yaxis=dict(visible=False, fixedrange=True),
            xaxis=dict(showgrid=False, tickfont=dict(size=13, family="Arial Black", color="white"), fixedrange=True)
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 5. TABS LAYOUT ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        # Din eksisterende tabel logik her...
        st.write(df_liga[['#', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P']])

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        if not df_wy_raw.empty:
            df_wy_raw.columns = [col.upper() for col in df_wy_raw.columns]
            df_agg = df_wy_raw.groupby('TEAMNAME').mean(numeric_only=True).reset_index()
            sub_tabs = st.tabs(["Offensivt", "Defensivt", "Spilopbygning"])
            with sub_tabs[0]: draw_h2h_chart_combined(team1, team2, ['XG', 'SHOTS'], ['xG', 'Skud'], df_agg)
            with sub_tabs[1]: draw_h2h_chart_combined(team1, team2, ['INTERCEPTIONS'], ['Interceptions'], df_agg)
            with sub_tabs[2]: draw_h2h_chart_combined(team1, team2, ['PASSES'], ['Afleveringer'], df_agg)
