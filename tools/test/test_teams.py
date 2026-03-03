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
    df = dp.get("opta", {}).get("matches", pd.DataFrame())
    
    if df.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # --- 1. HJÆLPEFUNKTIONER ---
    def get_logo_url(opta_uuid, team_name):
        wy_id = next((info.get('wyid') for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
        if wy_id and wy_id in logo_map:
            return logo_map[wy_id]
        return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

    def get_text_color(hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (r * 0.299 + g * 0.587 + b * 0.114)
        return "black" if luminance > 165 else "white"

    def update_form(current_form, result):
        form_list = list(current_form)
        form_list.append(result)
        return "".join(form_list[-5:])

    # --- 2. DATABEREGNING ---
    stats = {}
    for _, row in df.iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        h_g = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_g = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
        winner = str(row['WINNER']).lower()

        for uuid, name in [(h_uuid, h_name), (a_uuid, a_name)]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid, 'MATCHES': 0}

        if row['MATCH_STATUS'] == 'Played':
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            s_h['K'] += 1; s_a['K'] += 1
            s_h['MATCHES'] += 1; s_a['MATCHES'] += 1
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

    # Find næste modstander
    next_opponents_names = {}
    next_opponents_logos = {}
    df_upcoming = df[df['MATCH_STATUS'] != 'Played'].copy()
    for uuid in stats.keys():
        next_m = df_upcoming[(df_upcoming['CONTESTANTHOME_OPTAUUID'] == uuid) | 
                             (df_upcoming['CONTESTANTAWAY_OPTAUUID'] == uuid)].head(1)
        if not next_m.empty:
            row = next_m.iloc[0]
            is_home = row['CONTESTANTHOME_OPTAUUID'] == uuid
            opp_name = row['CONTESTANTAWAY_NAME'] if is_home else row['CONTESTANTHOME_NAME']
            opp_uuid = row['CONTESTANTAWAY_OPTAUUID'] if is_home else row['CONTESTANTHOME_OPTAUUID']
            next_opponents_names[uuid] = opp_name
            next_opponents_logos[uuid] = get_logo_url(opp_uuid, opp_name)
        else:
            next_opponents_names[uuid] = "-"
            next_opponents_logos[uuid] = None

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga['LOGO'] = df_liga['UUID'].apply(lambda x: get_logo_url(x, ""))
    df_liga['NÆSTE_LOG'] = df_liga['UUID'].map(next_opponents_logos)
    df_liga['NÆSTE_HOLD'] = df_liga['UUID'].map(next_opponents_names)
    
    # Sortering for indledende rank
    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, 'RANK', df_liga.index + 1)

    # --- 3. GRAF FUNKTION ---
    def draw_h2h_chart(n1, n2, metrics, labels, per_match=False):
        t1 = df_liga[df_liga['HOLD'] == n1].iloc[0].to_dict()
        t2 = df_liga[df_liga['HOLD'] == n2].iloc[0].to_dict()
        fig = go.Figure()
        
        y1_vals = [t1[m] / t1['MATCHES'] if per_match and t1['MATCHES'] > 0 else t1[m] for m in metrics]
        y2_vals = [t2[m] / t2['MATCHES'] if per_match and t2['MATCHES'] > 0 else t2[m] for m in metrics]
        
        c1 = colors_dict.get(n1, {"primary": "#cc0000"})
        c2 = colors_dict.get(n2, {"primary": "#0056a3"})
        
        bar_width = 0.25
        for i, trace in enumerate([(n1, y1_vals, c1), (n2, y2_vals, c2)]):
            fig.add_trace(go.Bar(
                name=trace[0], x=labels, y=trace[1], 
                marker_color=trace[2]["primary"],
                text=[f"{v:.1f}" if per_match else int(v) for v in trace[1]], 
                textposition='inside', width=bar_width,
                insidetextfont=dict(size=16, color=get_text_color(trace[2]["primary"]), family="Arial Black")
            ))

        for i in range(len(labels)):
            url1 = logo_map.get(n1) or get_logo_url(t1['UUID'], n1)
            url2 = logo_map.get(n2) or get_logo_url(t2['UUID'], n2)
            if url1:
                fig.add_layout_image(dict(source=url1, xref="x", yref="paper", x=i-0.20, y=1.15, sizex=0.10, sizey=0.10, xanchor="center", yanchor="middle"))
            if url2:
                fig.add_layout_image(dict(source=url2, xref="x", yref="paper", x=i+0.20, y=1.15, sizex=0.10, sizey=0.10, xanchor="center", yanchor="middle"))

        fig.update_layout(
            barmode='group', bargap=0.25, height=450, margin=dict(t=110, b=40, l=10, r=10),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False,
            yaxis=dict(visible=False, fixedrange=True, range=[0, max(max(y1_vals), max(y2_vals)) * 1.2]),
            xaxis=dict(fixedrange=True, tickfont=dict(size=14, family="Arial Black"))
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 4. LAYOUT ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        # Forberedelse af data til st.dataframe
        # Vi samler Logo og Navn i Næste-kolonnen ved hjælp af tekst (da st.dataframe ikke blander billeder/tekst i én celle let)
        df_view = df_liga[['RANK', 'LOGO', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM', 'NÆSTE_LOG', 'NÆSTE_HOLD']].copy()

        st.dataframe(
            df_view,
            column_config={
                "RANK": st.column_config.NumberColumn("Pos", help="Placering", format="%d"),
                "LOGO": st.column_config.ImageColumn("", help="Hold logo"),
                "HOLD": st.column_config.TextColumn("Hold"),
                "K": st.column_config.NumberColumn("K"),
                "V": st.column_config.NumberColumn("V"),
                "U": st.column_config.NumberColumn("U"),
                "T": st.column_config.NumberColumn("T"),
                "MD": st.column_config.NumberColumn("MD"),
                "P": st.column_config.NumberColumn("P"),
                "FORM": st.column_config.TextColumn("Form"),
                "NÆSTE_LOG": st.column_config.ImageColumn("Næste"),
                "NÆSTE_HOLD": st.column_config.TextColumn("Modstander")
            },
            hide_index=True,
            use_container_width=True
        )

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Vælg Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Vælg Hold 2", [h for h in h_list if h != team1])

        sub_tabs = st.tabs(["Generelt", "Offensivt", "Defensivt"])
        with sub_tabs[0]: draw_h2h_chart(team1, team2, ['P', 'V', 'K'], ['Point', 'Sejre', 'Kampe'])
        with sub_tabs[1]: draw_h2h_chart(team1, team2, ['M+'], ['Mål Scoret'])
        with sub_tabs[2]: draw_h2h_chart(team1, team2, ['M-'], ['Mål Imod'])
