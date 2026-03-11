import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
# Antager at du har en database connector
# from data.db_connection import run_query 

def vis_side(df_raw=None):
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet.")
        return
        
    dp = st.session_state["dp"]
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    logo_map = dp.get("logo_map", {})
    
    # --- 1. SQL INTEGRATION (DIN OPDATEREDE QUERY) ---
    # Vi henter rådata for alle kampe i ligaen for at beregne gennemsnit
    query_league_matches = """
    SELECT 
        tm.TEAM_WYID, 
        tm.MATCH_WYID,
        adv.SHOTS,
        adv.XG,
        adv.TOUCHESINBOX,
        md.PPDA,
        mp.PROGRESSIVEPASSESSUCCESSFUL as PROG_PASS_OK,
        mp.FORWARDPASSES
    FROM WYSCOUT_TEAMMATCHES tm
    LEFT JOIN WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv 
        ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID
    LEFT JOIN WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md 
        ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID
    LEFT JOIN WYSCOUT_MATCHADVANCEDSTATS_PASSES mp 
        ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID
    JOIN WYSCOUT_MATCHES m ON tm.MATCH_WYID = m.MATCH_WYID
    JOIN WYSCOUT_SEASONS s ON m.SEASON_WYID = s.SEASON_WYID
    WHERE tm.COMPETITION_WYID = 328
    AND s.SEASONNAME LIKE '2025%2026'
    """
    
    # Hent data (Her simuleret via session_state eller run_query)
    # df_raw_sql = run_query(query_league_matches) 
    df_raw_sql = dp.get("league_matches_raw", pd.DataFrame()) 

    if not df_raw_sql.empty:
        # Beregn gennemsnit per hold (Group By i Python for fleksibilitet)
        df_adv = df_raw_sql.groupby('TEAM_WYID').agg({
            'SHOTS': 'mean',
            'XG': 'mean',
            'PPDA': 'mean',
            'FORWARDPASSES': 'mean',
            'TOUCHESINBOX': 'mean',
            'PROG_PASS_OK': 'mean'
        }).reset_index()
    else:
        df_adv = pd.DataFrame()

    # Hent Opta data (Resultater og stilling)
    df_opta = dp.get("opta", {}).get("matches", pd.DataFrame())
    
    if df_opta.empty:
        st.warning("Ingen Opta kampdata fundet.")
        return

    # --- 2. HJÆLPEFUNKTIONER ---
    opta_to_wyid = {info['opta_uuid']: info['team_wyid'] for name, info in TEAMS.items() if 'opta_uuid' in info}

    def get_logo_url(opta_uuid):
        wy_id = opta_to_wyid.get(opta_uuid)
        return logo_map.get(wy_id, "")

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

    # --- 3. BEREGN LIGASTILLING (OPTA) ---
    stats = {}
    for _, row in df_opta.iterrows():
        if row['MATCH_STATUS'] != 'Played': continue
        
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        h_g, a_g = int(row.get('TOTAL_HOME_SCORE', 0)), int(row.get('TOTAL_AWAY_SCORE', 0))
        winner = str(row.get('WINNER', '')).lower()

        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid}

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

    # Omdan til DataFrame og Merge med Wyscout stats
    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga['TEAM_WYID'] = df_liga['UUID'].map(opta_to_wyid)
    
    if not df_adv.empty:
        df_liga = df_liga.merge(df_adv, on='TEAM_WYID', how='left')

    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- 4. GRAF FUNKTION ---
    def draw_h2h_chart(n1, n2, metrics, labels):
        t1 = df_liga[df_liga['HOLD'] == n1].iloc[0]
        t2 = df_liga[df_liga['HOLD'] == n2].iloc[0]
        fig = go.Figure()
        
        for name, data, color_key in [(n1, t1, n1), (n2, t2, n2)]:
            c = colors_dict.get(color_key, {"primary": "#888888"})
            vals = [data.get(m, 0) for m in metrics]
            fig.add_trace(go.Bar(
                name=name, x=labels, y=vals, 
                marker_color=c["primary"],
                text=[f"{v:.1f}" if isinstance(v, float) else int(v) for v in vals],
                textposition='inside'
            ))

        fig.update_layout(barmode='group', height=350, margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 5. VISNING ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', df_disp['UUID'].apply(get_logo_html))
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        
        # Omdøb til pæne navne til tabellen
        df_disp = df_disp.rename(columns={
            'SHOTS': 'Skud/K', 
            'FORWARDPASSES': 'Fwd P', 
            'PPDA': 'PPDA',
            'TOUCHESINBOX': 'Box Touches'
        })
        
        vis_cols = ['#', ' ', 'HOLD', 'K', 'P', 'Skud/K', 'Box Touches', 'PPDA', 'FORM']
        st.write(df_disp[vis_cols].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        s1, s2, s3 = st.tabs(["Resultater", "Offensiv (Wyscout)", "Pres & Opbygning"])
        with s1: 
            draw_h2h_chart(team1, team2, ['P', 'V', 'M+'], ['Point', 'Sejre', 'Mål'])
        with s2: 
            draw_h2h_chart(team1, team2, ['SHOTS', 'XG', 'TOUCHESINBOX'], ['Skud', 'xG', 'Box Touches'])
        with s3: 
            draw_h2h_chart(team1, team2, ['PPDA', 'PROG_PASS_OK'], ['PPDA (Pres)', 'Prog. Passes'])
