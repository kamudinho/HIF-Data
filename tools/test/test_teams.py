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

    # --- 1. HJÆLPEFUNKTIONER ---
    def get_logo_url(opta_uuid, team_name):
        logo_map = dp.get("logo_map", {})
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

    # --- 3. GRAF FUNKTION ---
    def draw_h2h_chart(t1, t2, metrics, labels):
        s1 = df_liga[df_liga['HOLD'] == t1].iloc[0]
        s2 = df_liga[df_liga['HOLD'] == t2].iloc[0]
        u1, u2 = s1['UUID'], s2['UUID']
        
        c1_hex = colors_dict.get(t1, {}).get('primary', '#cc0000')
        c2_hex = colors_dict.get(t2, {}).get('primary', '#0056a3')
        
        logo1 = get_logo_url(u1, t1)
        logo2 = get_logo_url(u2, t2)

        # 1. LOGO-RÆKKE (Nu korrekt samlet i én markdown blok)
        logo_items_html = ""
        for label in labels:
            logo_items_html += f"""
                <div style="flex: 1; display: flex; justify-content: center; align-items: center; gap: 38px;">
                    <img src="{logo1}" width="30" style="object-fit: contain;">
                    <img src="{logo2}" width="30" style="object-fit: contain;">
                </div>
            """

        st.markdown(
            f"""
            <div style="display: flex; width: 100%; padding: 0 40px; margin-bottom: -35px;">
                {logo_items_html}
            </div>
            """, 
            unsafe_allow_html=True
        )

        # 2. PLOTLY GRAF
        fig = go.Figure()
        x_vals = list(range(len(labels)))

        fig.add_trace(go.Bar(
            x=x_vals, y=[s1[m] for m in metrics],
            marker_color=c1_hex, text=[s1[m] for m in metrics], textposition='inside',
            insidetextfont=dict(size=16, color=get_text_color(c1_hex), family="Arial Black"),
            width=0.4
        ))
        
        fig.add_trace(go.Bar(
            x=x_vals, y=[s2[m] for m in metrics],
            marker_color=c2_hex, text=[s2[m] for m in metrics], textposition='inside',
            insidetextfont=dict(size=16, color=get_text_color(c2_hex), family="Arial Black"),
            width=0.4
        ))

        fig.update_layout(
            showlegend=False, 
            height=380, 
            margin=dict(t=10, b=40, l=40, r=40), # Skal matche padding (40px) i HTML ovenfor
            xaxis=dict(tickvals=x_vals, ticktext=labels, fixedrange=True),
            yaxis=dict(visible=False, fixedrange=True),
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            bargap=0.2,
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 4. LAYOUT ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
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
