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
    
    # --- 1. DATABEREGNING (WYSCOUT) ---
    df_raw_sql = dp.get("league_matches_raw", pd.DataFrame()) 

    if not df_raw_sql.empty:
        # Tving kolonnenavne til UPPERCASE for at matche SQL output
        df_raw_sql.columns = df_raw_sql.columns.str.upper()
        
        # Beregn gennemsnit per hold
        # Rettet: 'TOUCHINBOX' -> 'TOUCHESINBOX'
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

    # Hent Opta data
    df_opta = dp.get("opta", {}).get("matches", pd.DataFrame())
    if df_opta.empty:
        st.warning("Ingen Opta kampdata fundet.")
        return

    # --- 2. HJÆLPEFUNKTIONER ---
    opta_to_wyid = {info['opta_uuid']: info['team_wyid'] for name, info in TEAMS.items() if 'opta_uuid' in info}

    def get_logo_html(uuid):
        wy_id = opta_to_wyid.get(uuid)
        url = logo_map.get(wy_id, "")
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

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga['TEAM_WYID'] = df_liga['UUID'].map(opta_to_wyid)
    
    # Merge og sikring af typer
    if not df_adv.empty:
        df_liga['TEAM_WYID'] = pd.to_numeric(df_liga['TEAM_WYID'], errors='coerce')
        df_adv['TEAM_WYID'] = pd.to_numeric(df_adv['TEAM_WYID'], errors='coerce')
        df_liga = df_liga.merge(df_adv, on='TEAM_WYID', how='left')

    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- 4. VISNING ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', df_disp['UUID'].apply(get_logo_html))
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        
        # Sikker omdøbning (tjekker om kolonnen findes)
        rename_dict = {
            'SHOTS': 'Skud/K', 
            'FORWARDPASSES': 'Fwd P', 
            'PPDA': 'PPDA',
            'TOUCHESINBOX': 'Box Touches'
        }
        df_disp = df_disp.rename(columns={k: v for k, v in rename_dict.items() if k in df_disp.columns})
        
        # Dynamisk kolonnevalg for at undgå 'Index Error'
        vis_cols = ['#', ' ', 'HOLD', 'K', 'P']
        # Tilføj de avancerede kolonner hvis de findes efter omdøbning
        for c in ['Skud/K', 'Box Touches', 'PPDA']:
            if c in df_disp.columns:
                vis_cols.append(c)
        vis_cols.append('FORM')
        
        st.write(df_disp[vis_cols].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        # Grafer med de korrekte kolonnenavne fra din SQL
        s1, s2, s3 = st.tabs(["Resultater", "Offensiv", "Pres & Opbygning"])
        
        def draw_h2h_chart(n1, n2, metrics, labels):
            # Samme funktion som før, men tjekker .get() for at undgå fejl
            t1 = df_liga[df_liga['HOLD'] == n1].iloc[0]
            t2 = df_liga[df_liga['HOLD'] == n2].iloc[0]
            fig = go.Figure()
            for name, data, color_key in [(n1, t1, n1), (n2, t2, n2)]:
                c = colors_dict.get(color_key, {"primary": "#888888"})
                vals = [data.get(m, 0) for m in metrics]
                fig.add_trace(go.Bar(name=name, x=labels, y=vals, marker_color=c["primary"]))
            fig.update_layout(barmode='group', height=300)
            st.plotly_chart(fig, use_container_width=True)

        with s1: draw_h2h_chart(team1, team2, ['P', 'V', 'M+'], ['Point', 'Sejre', 'Mål'])
        with s2: draw_h2h_chart(team1, team2, ['SHOTS', 'XG', 'TOUCHESINBOX'], ['Skud', 'xG', 'Box Touches'])
        with s3: draw_h2h_chart(team1, team2, ['PPDA', 'PROG_PASS_OK'], ['PPDA', 'Prog. Pass'])
