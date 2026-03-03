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
    
    # Hent data fra din opta_matches query
    df = dp.get("opta", {}).get("matches", pd.DataFrame())
    
    if df.empty:
        st.warning("Ingen kampdata fundet. Tjek din Snowflake forbindelse.")
        return

    # --- 1. BEREGNING AF STATISTIK ---
    stats = {}

    # Hjælpefunktion til at opdatere form (V-U-T)
    def update_form(current_form, result):
        form_list = list(current_form)
        form_list.append(result)
        return "".join(form_list[-5:]) # Behold kun de sidste 5

    for _, row in df.iterrows():
        # Baseret på din rå data-struktur:
        h_uuid = row['CONTESTANTHOME_OPTAUUID']
        a_uuid = row['CONTESTANTAWAY_OPTAUUID']
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        winner = str(row['WINNER']).lower()
        
        # Målscore
        h_goals = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_goals = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0

        # Initialiser hold hvis de mangler
        for uuid, name in [(h_uuid, h_name), (a_uuid, a_name)]:
            if uuid not in stats:
                stats[uuid] = {
                    'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 
                    'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid
                }

        # Vi tæller kun kampe der er "Played"
        if row['MATCH_STATUS'] == 'Played':
            s_h = stats[h_uuid]
            s_a = stats[a_uuid]
            
            s_h['K'] += 1
            s_a['K'] += 1
            s_h['M+'] += h_goals
            s_h['M-'] += a_goals
            s_a['M+'] += a_goals
            s_a['M-'] += h_goals

            if winner == 'home':
                s_h['V'] += 1; s_h['P'] += 3; s_h['FORM'] = update_form(s_h['FORM'], 'V')
                s_a['T'] += 1; s_a['FORM'] = update_form(s_a['FORM'], 'T')
            elif winner == 'away':
                s_a['V'] += 1; s_a['P'] += 3; s_a['FORM'] = update_form(s_a['FORM'], 'V')
                s_h['T'] += 1; s_h['FORM'] = update_form(s_h['FORM'], 'T')
            else:
                s_h['U'] += 1; s_h['P'] += 1; s_h['FORM'] = update_form(s_h['FORM'], 'U')
                s_a['U'] += 1; s_a['P'] += 1; s_a['FORM'] = update_form(s_a['FORM'], 'U')

    # Lav til DataFrame og sorter
    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.index += 1 # Plads nummer 1, 2, 3...

    # --- 2. VISNING ---
    st.subheader("Superliga Stilling (Opta Data)")

    # Mapping af logoer
    def get_logo(uuid):
        logo = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == uuid), "")
        return f'<img src="{logo}" width="25">' if logo else ""

    df_display = df_liga.copy()
    df_display.insert(0, ' ', [get_logo(u) for u in df_display['UUID']])
    
    # Styling af FORM kolonne (Farver)
    def style_form(form_str):
        res = ""
        for char in form_str:
            color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
            res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
        return res
    
    df_display['FORM'] = df_display['FORM'].apply(style_form)

    # Tabelvisning
    cols_to_show = [' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']
    st.write(df_display[cols_to_show].to_html(escape=False, index=True), unsafe_allow_html=True)

    # --- 3. HEAD-TO-HEAD GRAFIK ---
    st.divider()
    col1, col2 = st.columns(2)
    h_list = df_liga['HOLD'].tolist()
    team1 = col1.selectbox("Vælg Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
    team2 = col2.selectbox("Vælg Hold 2", [h for h in h_list if h != team1])

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

    fig.update_layout(barmode='group', height=300, margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)
