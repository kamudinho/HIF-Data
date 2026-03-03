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
    df = dp.get("opta", {}).get("matches", pd.DataFrame())
    
    if df.empty:
        st.warning("Ingen kampdata fundet i 'dp'.")
        return

    # --- 1. DATA PROCESSING ---
    stats = {}
    def update_form(current_form, result):
        form_list = list(current_form)
        form_list.append(result)
        return "".join(form_list[-5:])

    for _, row in df.iterrows():
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
    df_liga.index += 1

    # --- 2. HOVED LAYOUT ---
    main_tabs = st.tabs(["Ligaoversigt", "Head-to-head"])

    # --- TAB 1: LIGAOVERSIGT ---
    with main_tabs[0]:
        st.subheader("Ligaoversigt")
        
        def get_logo_html(uuid):
            logo = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == uuid), "")
            return f'<img src="{logo}" width="20">' if logo else ""

        def style_form(form_str):
            res = ""
            for char in form_str:
                color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
                res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
            return res

        df_disp = df_liga.copy()
        df_disp.insert(0, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        
        st.write(df_disp[[' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=True), unsafe_allow_html=True)

    # --- TAB 2: HEAD-TO-HEAD ---
    with main_tabs[1]:
        st.subheader("Sammenlign Hold")
        
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        
        with c1:
            team1 = st.selectbox("Vælg Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
            st.image(TEAMS.get(team1, {}).get('logo', ""), width=60)
            
        with c2:
            team2 = st.selectbox("Vælg Hold 2", [h for h in h_list if h != team1])
            st.image(TEAMS.get(team2, {}).get('logo', ""), width=60)

        # Under-tabs til statistik
        sub_tabs = st.tabs(["Generelt", "Offensivt", "Defensivt"])
        
        def make_chart(metrics, labels):
            s1 = df_liga[df_liga['HOLD'] == team1].iloc[0]
            s2 = df_liga[df_liga['HOLD'] == team2].iloc[0]
            fig = go.Figure()
            fig.add_trace(go.Bar(name=team1, x=labels, y=[s1[m] for m in metrics], 
                                 marker_color=colors_dict.get(team1, {}).get('primary', '#cc0000'), textposition='auto'))
            fig.add_trace(go.Bar(name=team2, x=labels, y=[s2[m] for m in metrics], 
                                 marker_color=colors_dict.get(team2, {}).get('primary', '#0056a3'), textposition='auto'))
            fig.update_layout(barmode='group', showlegend=False, height=300, margin=dict(t=10, b=10, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

        with sub_tabs[0]:
            make_chart(['P', 'V', 'K'], ['Point', 'Sejre', 'Kampe'])
        with sub_tabs[1]:
            make_chart(['M+'], ['Mål Scoret'])
        with sub_tabs[2]:
            make_chart(['M-'], ['Mål Imod'])
