import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

# --- 1. GLOBALE HJÆLPEFUNKTIONER ---

def get_text_color(hex_color):
    if not hex_color: return "white"
    hex_color = str(hex_color).lstrip('#')
    if len(hex_color) != 6: return "white"
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (r * 0.299 + g * 0.587 + b * 0.114)
    return "black" if luminance > 165 else "white"

# --- 2. HOVEDSIDE ---

def vis_side(df_raw=None):
    if "dp" not in st.session_state: 
        st.error("Data pakken 'dp' mangler.")
        return
    
    dp = st.session_state["dp"]
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    logo_map = dp.get("logo_map", {})
    df_opta = dp.get("opta", {}).get("matches", pd.DataFrame())
    
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"

    # --- HJÆLPEFUNKTIONER ---
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

    # --- DATABEREGNING (OPTA LIGATABEL) ---
    stats = {}
    if not df_opta.empty:
        for _, row in df_opta.iterrows():
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

    df_liga = pd.DataFrame(stats.values())
    if not df_liga.empty:
        df_liga['MD'] = df_liga['M+'] - df_liga['M-']
        df_liga = df_liga.sort_values(by=['P', 'MD'], ascending=False).reset_index(drop=True)
        df_liga.insert(0, '#', df_liga.index + 1)

    # --- WYSCOUT DATA HENTNING (RETTET SQL) ---
    @st.cache_data(ttl=600)
    def get_wyscout_direct():
        if conn is None: return pd.DataFrame()
        # Jeg har fjernet TOUCHINBOX da den fejlede - vi finder det korrekte navn senere
        query = f"""
        SELECT 
            t.TEAMNAME,
            adv.XG, adv.SHOTS,
            md.RECOVERIES, md.INTERCEPTIONS,
            mp.PASSES
        FROM {DB}.WYSCOUT_TEAMMATCHES tm
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID
        JOIN {DB}.WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
        JOIN {DB}.WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
        JOIN {DB}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID
        WHERE tm.COMPETITION_WYID = 328
        AND s.SEASONNAME LIKE '2025%2026'
        """
        try:
            return conn.query(query)
        except Exception as e:
            st.error(f"SQL Fejl ved hentning af Wyscout: {e}")
            return pd.DataFrame()

    df_wy_raw = get_wyscout_direct()

    # --- LAYOUT ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        if not df_liga.empty:
            st.markdown("""<style>.league-table { width: 100%; border-collapse: collapse; font-size: 14px; } 
                        .league-table td, .league-table th { padding: 8px; text-align: center; border-bottom: 1px solid #eee; }</style>""", unsafe_allow_html=True)
            df_disp = df_liga.copy()
            df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
            df_disp['FORM'] = df_disp['FORM'].apply(style_form)
            st.write(df_disp[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_h2h:
        if df_liga.empty: return
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        if not df_wy_raw.empty:
            df_wy_raw.columns = [c.upper() for c in df_wy_raw.columns]
            df_agg = df_wy_raw.groupby('TEAMNAME').mean(numeric_only=True).reset_index()
            
            d1 = df_agg[df_agg['TEAMNAME'].str.contains(team1, case=False, na=False)]
            d2 = df_agg[df_agg['TEAMNAME'].str.contains(team2, case=False, na=False)]

            if not d1.empty and not d2.empty:
                st.subheader("Wyscout Performance (Gns. pr. kamp)")
                # Vi har fjernet TOUCHINBOX herunder også
                cats = {
                    "Angreb": (['XG', 'SHOTS'], ['xG', 'Skud']),
                    "Forsvar": (['RECOVERIES', 'INTERCEPTIONS'], ['Genvindinger', 'Interceptions']),
                    "Spilopbygning": (['PASSES'], ['Afleveringer'])
                }
                
                c_tabs = st.tabs(list(cats.keys()))
                for i, (name, (metrics, labels)) in enumerate(cats.items()):
                    with c_tabs[i]:
                        v1 = [d1.iloc[0].get(m, 0) for m in metrics]
                        v2 = [d2.iloc[0].get(m, 0) for m in metrics]
                        fig = go.Figure()
                        fig.add_trace(go.Bar(name=team1, x=labels, y=v1, marker_color="#df003b", text=[f"{x:.2f}" for x in v1], textposition='auto'))
                        fig.add_trace(go.Bar(name=team2, x=labels, y=v2, marker_color="#0056a3", text=[f"{x:.2f}" for x in v2], textposition='auto'))
                        fig.update_layout(barmode='group', height=350, margin=dict(t=20, b=20, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"Ingen match i database for {team1} eller {team2}.")
        else:
            st.error("Kunne ikke hente data. Tjek om sæson/liga findes i Snowflake.")
