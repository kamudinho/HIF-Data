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
        st.warning("Ingen kampdata fundet.")
        return

    # --- 1. BEREGNING AF STATISTIK ---
    stats = {}

    def update_form(current_form, result):
        form_list = list(current_form)
        form_list.append(result)
        return "".join(form_list[-5:])

    for _, row in df.iterrows():
        h_uuid = row['CONTESTANTHOME_OPTAUUID']
        a_uuid = row['CONTESTANTAWAY_OPTAUUID']
        h_name = row['CONTESTANTHOME_NAME']
        winner = str(row['WINNER']).lower()
        
        h_goals = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_goals = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0

        for uuid, name in [(h_uuid, h_name), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid}

        if row['MATCH_STATUS'] == 'Played':
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            s_h['K'] += 1; s_a['K'] += 1
            s_h['M+'] += h_goals; s_h['M-'] += a_goals
            s_a['M+'] += a_goals; s_a['M-'] += h_goals
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

    # Hjælpefunktioner til logoer
    def get_logo_html(uuid):
        logo = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == uuid), "")
        return f'<img src="{logo}" width="25">' if logo else ""

    def get_logo_url(team_name):
        return TEAMS.get(team_name, {}).get('logo', "")

    # --- 2. TABS ---
    tab1, tab2 = st.tabs(["Ligaoversigt", "Bar Charts"])

    with tab1:
        st.subheader("Stilling")
        df_display = df_liga.copy()
        df_display.insert(0, ' ', [get_logo_html(u) for u in df_display['UUID']])
        
        def style_form(form_str):
            res = ""
            for char in form_str:
                color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
                res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
            return res
        
        df_display['FORM'] = df_display['FORM'].apply(style_form)
        st.write(df_display[[' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=True), unsafe_allow_html=True)

    with tab2:
        st.subheader("Sammenlign Hold")
        h_list = sorted(df_liga['HOLD'].tolist())
        
        col_a, col_b = st.columns(2)
        
        # Hold 1 valg + Logo
        with col_a:
            team1 = st.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
            logo1 = get_logo_url(team1)
            if logo1: st.image(logo1, width=60)

        # Hold 2 valg + Logo
        with col_b:
            team2 = st.selectbox("Hold 2", [h for h in h_list if h != team1])
            logo2 = get_logo_url(team2)
            if logo2: st.image(logo2, width=60)

        # Bar Chart logik
        s1 = df_liga[df_liga['HOLD'] == team1].iloc[0]
        s2 = df_liga[df_liga['HOLD'] == team2].iloc[0]

        fig = go.Figure()
        metrics = ['P', 'V', 'M+']
        labels = ['Point', 'Sejre', 'Mål Scoret']
        
        for i, m in enumerate(metrics):
            fig.add_trace(go.Bar(
                name=team1, x=[labels[i]], y=[s1[m]],
                marker_color=colors_dict.get(team1, {}).get('primary', '#cc0000'),
                text=[s1[m]], textposition='auto'
            ))
            fig.add_trace(go.Bar(
                name=team2, x=[labels[i]], y=[s2[m]],
                marker_color=colors_dict.get(team2, {}).get('primary', '#0056a3'),
                text=[s2[m]], textposition='auto'
            ))

        fig.update_layout(
            barmode='group', height=400, margin=dict(t=10, b=10, l=0, r=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)
