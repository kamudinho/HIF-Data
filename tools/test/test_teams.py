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
    logo_map = dp.get("logo_map", {}) # Hentes her så den er tilgængelig i funktioner
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
                # Vi tilføjer 'MATCHES' her så din create_h2h_plot ikke fejler ved division
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid, 'MATCHES': 0}

        if row['MATCH_STATUS'] == 'Played':
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            s_h['K'] += 1; s_a['K'] += 1
            s_h['MATCHES'] += 1; s_a['MATCHES'] += 1
            s_h['M+'] += h_g; s_h['M-'] += a_g
            s_a['M+'] += a_g; s_a['M-'] += h_g
            # ... (form-logik forbliver uændret)
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

    # --- 3. GRAF FUNKTION (Indlejret Plotly-logo version) ---
    def draw_h2h_chart(n1, n2, metrics, labels, per_match=False):
        # Hent data
        t1 = df_liga[df_liga['HOLD'] == n1].iloc[0].to_dict()
        t2 = df_liga[df_liga['HOLD'] == n2].iloc[0].to_dict()
        
        fig = go.Figure()
        
        y1_vals = [t1[m] / t1['MATCHES'] if per_match and t1['MATCHES'] > 0 else t1[m] for m in metrics]
        y2_vals = [t2[m] / t2['MATCHES'] if per_match and t2['MATCHES'] > 0 else t2[m] for m in metrics]
        
        # Farver fra din config
        c1 = colors_dict.get(n1, {"primary": "#cc0000", "secondary": "#000000"})
        c2 = colors_dict.get(n2, {"primary": "#0056a3", "secondary": "#000000"})
        
        # Søjler
        bar_width = 0.4 # Øget en smule for bedre fylde
        
        fig.add_trace(go.Bar(
            name=n1, x=labels, y=y1_vals, 
            marker_color=c1["primary"],
            text=[f"{v:.1f}" if per_match else int(v) for v in y1_vals], 
            textposition='inside',
            width=bar_width,
            insidetextfont=dict(size=16, color=get_text_color(c1["primary"]), family="Arial Black")
        ))
        
        fig.add_trace(go.Bar(
            name=n2, x=labels, y=y2_vals, 
            marker_color=c2["primary"],
            text=[f"{v:.1f}" if per_match else int(v) for v in y2_vals], 
            textposition='inside',
            width=bar_width,
            insidetextfont=dict(size=16, color=get_text_color(c2["primary"]), family="Arial Black")
        ))

        # Logo-placering med optimerede offsets
        for i in range(len(labels)):
            url1 = get_logo_url(t1['UUID'], n1)
            url2 = get_logo_url(t2['UUID'], n2)
            
            if url1:
                fig.add_layout_image(dict(
                    source=url1, xref="x", yref="paper", x=i - 0.22, y=1.18,
                    sizex=0.15, sizey=0.15, xanchor="center", yanchor="middle"
                ))
            if url2:
                fig.add_layout_image(dict(
                    source=url2, xref="x", yref="paper", x=i + 0.22, y=1.18,
                    sizex=0.15, sizey=0.15, xanchor="center", yanchor="middle"
                ))

        fig.update_layout(
            barmode='group', 
            bargap=0.3, # Gør grupperne lidt bredere
            bargroupgap=0.02, # Minimale mellemrum mellem hold-barerne
            height=450, 
            margin=dict(t=120, b=40, l=10, r=10),
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            yaxis=dict(visible=False, fixedrange=True),
            xaxis=dict(fixedrange=True, tickfont=dict(size=14, family="Arial Black"))
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 4. LAYOUT ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        # (Din tabel-logik her...)
        def get_logo_html(uuid):
            url = get_logo_url(uuid, "")
            return f'<img src="{url}" width="20">' if url else ""
        
        def style_form(f):
            res = ""
            for char in f:
                color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
                res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
            return res

        df_disp = df_liga.copy()
        df_disp.insert(0, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        st.write(df_disp[[' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P', 'FORM']].to_html(escape=False, index=True), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Vælg Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Vælg Hold 2", [h for h in h_list if h != team1])

        sub_tabs = st.tabs(["Generelt", "Offensivt", "Defensivt"])
        with sub_tabs[0]:
            draw_h2h_chart(team1, team2, ['P', 'V', 'K'], ['Point', 'Sejre', 'Kampe'])
        with sub_tabs[1]:
            draw_h2h_chart(team1, team2, ['M+'], ['Mål Scoret'])
        with sub_tabs[2]:
            draw_h2h_chart(team1, team2, ['M-'], ['Mål Imod'])
