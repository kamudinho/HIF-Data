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
    # BEREGN MD HER:
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    # SORTERING (P, så MD, så M+):
    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.index += 1

    def get_text_color(hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return "black" if (r * 0.299 + g * 0.587 + b * 0.114) > 186 else "white"

    # --- 2. TABS ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
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
        
        # MD er nu med i kolonne-listen
        st.write(df_disp[[' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=True), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        sub_tabs = st.tabs(["Generelt", "Offensivt", "Defensivt"])

        def draw_h2h_chart(metrics, labels):
            s1 = df_liga[df_liga['HOLD'] == team1].iloc[0]
            s2 = df_liga[df_liga['HOLD'] == team2].iloc[0]
            
            c1_hex = colors_dict.get(team1, {}).get('primary', '#cc0000')
            c2_hex = colors_dict.get(team2, {}).get('primary', '#0056a3')
            
            logo1 = TEAMS.get(team1, {}).get('logo', "")
            logo2 = TEAMS.get(team2, {}).get('logo', "")

            fig = go.Figure()
            x_vals = list(range(len(labels)))

            # Bar 1
            fig.add_trace(go.Bar(
                x=x_vals, y=[s1[m] for m in metrics],
                marker_color=c1_hex, text=[s1[m] for m in metrics], textposition='inside',
                insidetextfont=dict(color=get_text_color(c1_hex)),
                width=0.35, offset=-0.37
            ))
            # Bar 2
            fig.add_trace(go.Bar(
                x=x_vals, y=[s2[m] for m in metrics],
                marker_color=c2_hex, text=[s2[m] for m in metrics], textposition='inside',
                insidetextfont=dict(color=get_text_color(c2_hex)),
                width=0.35, offset=0.02
            ))

            for i in x_vals:
                if logo1:
                    fig.add_layout_image(dict(
                        source=logo1, x=i-0.19, y=s1[metrics[i]], xref="x", yref="y",
                        sizex=0.18, sizey=0.18, xanchor="center", yanchor="bottom"
                    ))
                if logo2:
                    fig.add_layout_image(dict(
                        source=logo2, x=i+0.20, y=s2[metrics[i]], xref="x", yref="y",
                        sizex=0.18, sizey=0.18, xanchor="center", yanchor="bottom"
                    ))

            max_val = max(max([s1[m] for m in metrics]), max([s2[m] for m in metrics]), 1)
            fig.update_layout(
                showlegend=False, height=400, margin=dict(t=60, b=40, l=10, r=10),
                xaxis=dict(tickvals=x_vals, ticktext=labels),
                yaxis=dict(visible=False, range=[0, max_val * 1.3])
            )
            st.plotly_chart(fig, use_container_width=True)

        with sub_tabs[0]: draw_h2h_chart(['P', 'V', 'K'], ['Point', 'Sejre', 'Kampe'])
        with sub_tabs[1]: draw_h2h_chart(['M+'], ['Mål Scoret'])
        with sub_tabs[2]: draw_h2h_chart(['M-'], ['Mål Imod'])
