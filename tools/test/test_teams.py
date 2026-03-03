import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TOURNAMENTCALENDAR_NAME, TEAM_COLORS

def vis_side(df_raw=None):
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet.")
        return
        
    dp = st.session_state["dp"]
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    
    # Vi henter kampene fra 'opta_matches' i din data_package
    df = dp.get("opta", {}).get("matches", pd.DataFrame())
    
    if df.empty:
        st.warning("Ingen kampdata fundet i Snowflake. Tjek din query 'opta_matches'.")
        return

    # --- 1. BEREGNING AF LIGATABEL BASERET PÅ WINNER-KOLONNEN ---
    stats = {}

    for _, row in df.iterrows():
        # Hent info for denne kamp
        h_uuid = row['CONTESTANTHOME_OPTAUUID']
        a_uuid = row['CONTESTANTAWAY_OPTAUUID']
        h_name = row['CONTESTANTHOME_NAME']
        a_name = row['CONTESTANTAWAY_NAME']
        winner = str(row['WINNER']).lower()
        
        # Målscore
        h_goals = row.get('TOTAL_HOME_SCORE', 0)
        a_goals = row.get('TOTAL_AWAY_SCORE', 0)

        # Initialiser hold i vores stats-dict hvis de ikke findes
        for uuid, name in [(h_uuid, h_name), (a_uuid, a_name)]:
            if uuid not in stats:
                stats[uuid] = {
                    'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 
                    'M+': 0, 'M-': 0, 'P': 0, 'UUID': uuid
                }

        # Opdater stats
        stats[h_uuid]['K'] += 1
        stats[a_uuid]['K'] += 1
        stats[h_uuid]['M+'] += h_goals
        stats[h_uuid]['M-'] += a_goals
        stats[a_uuid]['M+'] += a_goals
        stats[a_uuid]['M-'] += h_goals

        if winner == 'home':
            stats[h_uuid]['V'] += 1
            stats[h_uuid]['P'] += 3
            stats[a_uuid]['T'] += 1
        elif winner == 'away':
            stats[a_uuid]['V'] += 1
            stats[a_uuid]['P'] += 3
            stats[h_uuid]['T'] += 1
        else: # draw
            stats[h_uuid]['U'] += 1
            stats[h_uuid]['P'] += 1
            stats[a_uuid]['U'] += 1
            stats[a_uuid]['P'] += 1

    # Lav dict om til DataFrame og beregn måldifference
    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)

    # --- 2. RENDER INTERFACE ---
    tab_liga, tab_h2h = st.tabs(["🏆 Ligaoversigt", "📊 Head-to-Head"])

    with tab_liga:
        # Tilføj logoer fra din TEAMS mapping
        def get_logo(uuid):
            # Find logo i TEAMS mapping via UUID
            logo = next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == uuid), None)
            return f'<img src="{logo}" width="25">' if logo else ""

        df_display = df_liga.copy()
        df_display.insert(0, '', df_display['UUID'].apply(get_logo))
        
        st.write(df_display.drop(columns=['UUID']).to_html(escape=False, index=False), unsafe_allow_html=True)

    with tab_h2h:
        c1, c2 = st.columns(2)
        hold_liste = df_liga['HOLD'].tolist()
        t1 = c1.selectbox("Vælg Hold 1", hold_liste, index=hold_liste.index("Hvidovre") if "Hvidovre" in hold_liste else 0)
        t2 = c2.selectbox("Vælg Hold 2", [h for h in hold_liste if h != t1])

        s1 = df_liga[df_liga['HOLD'] == t1].iloc[0]
        s2 = df_liga[df_liga['HOLD'] == t2].iloc[0]

        # Simpel sammenligning
        fig = go.Figure()
        metrics = ['P', 'V', 'M+']
        labels = ['Point', 'Sejre', 'Mål Scoret']
        
        for i, m in enumerate(metrics):
            fig.add_trace(go.Bar(
                name=t1, x=[labels[i]], y=[s1[m]],
                marker_color=colors_dict.get(t1, {}).get('primary', '#cc0000'),
                text=[s1[m]], textposition='auto'
            ))
            fig.add_trace(go.Bar(
                name=t2, x=[labels[i]], y=[s2[m]],
                marker_color=colors_dict.get(t2, {}).get('primary', '#0056a3'),
                text=[s2[m]], textposition='auto'
            ))

        fig.update_layout(barmode='group', height=350, margin=dict(t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
