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

    # --- 1. DATABEREGNING ---
    stats = {}
    for _, row in df.iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        winner = str(row['WINNER']).lower()
        h_g = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_g = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0

        for uuid, name in [(h_uuid, h_name), (a_uuid, a_name)]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'UUID': uuid}

        if row['MATCH_STATUS'] == 'Played':
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            s_h['K'] += 1; s_a['K'] += 1
            s_h['M+'] += h_g; s_h['M-'] += a_g
            s_a['M+'] += a_g; s_a['M-'] += h_g
            if winner == 'home': s_h['V'] += 1; s_h['P'] += 3; s_a['T'] += 1
            elif winner == 'away': s_a['V'] += 1; s_a['P'] += 3; s_h['T'] += 1
            else: s_h['U'] += 1; s_h['P'] += 1; s_a['U'] += 1; s_a['P'] += 1

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga['M_PR_K'] = (df_liga['M+'] / df_liga['K']).round(2)
    df_liga['MOD_PR_K'] = (df_liga['M-'] / df_liga['K']).round(2)
    df_liga = df_liga.sort_values(by=['P', 'MD'], ascending=False).reset_index(drop=True)

    # --- 2. TABS ---
    t_oversigt, t_gen, t_off, t_def = st.tabs(["Ligaoversigt", "Generelt", "Offensivt", "Defensivt"])

    with t_oversigt:
        st.write(df_liga[['HOLD', 'K', 'V', 'U', 'T', 'MD', 'P']].to_html(escape=False), unsafe_allow_html=True)

    # Funktion til at lave barchart med logoer
    def create_comparison_chart(t1, t2, metrics, labels):
        s1 = df_liga[df_liga['HOLD'] == t1].iloc[0]
        s2 = df_liga[df_liga['HOLD'] == t2].iloc[0]
        l1, l2 = TEAMS.get(t1, {}).get('logo', ""), TEAMS.get(t2, {}).get('logo', "")
        
        fig = go.Figure()
        for i, m in enumerate(metrics):
            # Bar for Hold 1
            fig.add_trace(go.Bar(x=[labels[i]], y=[s1[m]], name=t1, 
                                 marker_color=colors_dict.get(t1, {}).get('primary', '#cc0000'),
                                 offsetgroup=0, text=[s1[m]], textposition='auto'))
            # Bar for Hold 2
            fig.add_trace(go.Bar(x=[labels[i]], y=[s2[m]], name=t2, 
                                 marker_color=colors_dict.get(t2, {}).get('primary', '#0056a3'),
                                 offsetgroup=1, text=[s2[m]], textposition='auto'))
            
            # Tilføj logoer som annotations over hver bar
            if l1:
                fig.add_layout_image(dict(source=l1, x=i, y=s1[m], xref="x", yref="y",
                                        sizex=0.3, sizey=0.3, xanchor="right", yanchor="bottom"))
            if l2:
                fig.add_layout_image(dict(source=l2, x=i, y=s2[m], xref="x", yref="y",
                                        sizex=0.3, sizey=0.3, xanchor="left", yanchor="bottom"))

        fig.update_layout(showlegend=False, barmode='group', height=400, margin=dict(t=50))
        return fig

    # Selector til de tre stat-tabs
    h_list = sorted(df_liga['HOLD'].tolist())
    c1, c2 = st.columns(2)
    sel1 = c1.selectbox("Vælg Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0, key="s1")
    sel2 = c2.selectbox("Vælg Hold 2", [h for h in h_list if h != sel1], key="s2")

    with t_gen:
        st.plotly_chart(create_comparison_chart(sel1, sel2, ['P', 'K', 'V'], ['Point', 'Kampe', 'Sejre']), use_container_width=True)

    with t_off:
        st.plotly_chart(create_comparison_chart(sel1, sel2, ['M+', 'M_PR_K'], ['Mål Scoret', 'Mål pr. kamp']), use_container_width=True)

    with t_def:
        st.plotly_chart(create_comparison_chart(sel1, sel2, ['M-', 'MOD_PR_K'], ['Mål Imod', 'Imod pr. kamp']), use_container_width=True)
