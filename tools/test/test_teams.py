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

    df_liga = pd.DataFrame(stats.values()).sort_values(by=['P', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.index += 1

    # Hjælpefunktion til tekstfarve (Sort skrift på lyse farver)
    def get_text_color(hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # Luminans beregning: hvis lysere end 186 (på skala 0-255), brug sort skrift
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
        st.write(df_disp[[' ', 'HOLD', 'K', 'V', 'U', 'T', 'M+', 'P', 'FORM']].to_html(escape=False, index=True), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        sub_gen, sub_off, sub_def = st.tabs(["Generelt", "Offensivt", "Defensivt"])

        def draw_h2h_chart(metrics, labels):
            s1 = df_liga[df_liga['HOLD'] == team1].iloc[0]
            s2 = df_liga[df_liga['HOLD'] == team2].iloc[0]
            
            c1_hex = colors_dict.get(team1, {}).get('primary', '#cc0000')
            c2_hex = colors_dict.get(team2, {}).get('primary', '#0056a3')
            
            logo1 = TEAMS.get(team1, {}).get('logo', "")
            logo2 = TEAMS.get(team2, {}).get('logo', "")

            fig = go.Figure()
            
            # Søjler med tekst indeni
            fig.add_trace(go.Bar(
                name=team1, x=labels, y=[s1[m] for m in metrics],
                marker_color=c1_hex, text=[s1[m] for m in metrics], textposition='inside',
                insidetextfont=dict(color=get_text_color(c1_hex)), offsetgroup=1
            ))
            fig.add_trace(go.Bar(
                name=team2, x=labels, y=[s2[m] for m in metrics],
                marker_color=c2_hex, text=[s2[m] for m in metrics], textposition='inside',
                insidetextfont=dict(color=get_text_color(c2_hex)), offsetgroup=2
            ))

            # Tilføj logoer over hver bar via annotations/images
            for i in range(len(labels)):
                if logo1:
                    fig.add_layout_image(dict(
                        source=logo1, x=labels[i], y=s1[metrics[i]], xref="x", yref="y",
                        sizex=0.25, sizey=0.25, xanchor="right", yanchor="bottom"
                    ))
                if logo2:
                    fig.add_layout_image(dict(
                        source=logo2, x=labels[i], y=s2[metrics[i]], xref="x", yref="y",
                        sizex=0.25, sizey=0.25, xanchor="left", yanchor="bottom"
                    ))

            fig.update_layout(
                barmode='group', showlegend=False, height=400,
                margin=dict(t=50, b=20, l=0, r=0),
                yaxis=dict(visible=False) # Skjuler y-aksen da værdier står i bars
            )
            st.plotly_chart(fig, use_container_width=True)

        with sub_gen: draw_h2h_chart(['P', 'V', 'K'], ['Point', 'Sejre', 'Kampe'])
        with sub_off: draw_h2h_chart(['M+'], ['Mål Scoret'])
        with sub_def: draw_h2h_chart(['M-'], ['Mål Imod'])
