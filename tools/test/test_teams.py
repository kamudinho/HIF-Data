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
    
    # Hent data fra DP
    df_opta = dp.get("opta", {}).get("matches", pd.DataFrame())
    df_adv = dp.get("team_stats_full", pd.DataFrame()) # Din Wyscout query
    
    if df_opta.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # --- 1. HJÆLPEFUNKTIONER & MAPPING ---
    # Vi bygger en bro mellem Opta UUID og Wyscout TEAM_WYID via team_mapping.py
    opta_to_wyid = {info['opta_uuid']: info['team_wyid'] for name, info in TEAMS.items() if 'opta_uuid' in info}

    def get_logo_url(opta_uuid, team_name):
        wy_id = opta_to_wyid.get(opta_uuid)
        if wy_id and wy_id in logo_map:
            return logo_map[wy_id]
        return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

    def get_logo_html(uuid):
        url = get_logo_url(uuid, "")
        return f'<img src="{url}" width="20">' if url else ""

    def get_text_color(hex_color):
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (r * 0.299 + g * 0.587 + b * 0.114)
        return "black" if luminance > 165 else "white"

    def update_form(current_form, result):
        form_list = list(current_form)
        form_list.append(result)
        return "".join(form_list[-5:])

    def style_form(f):
        res = ""
        for char in f:
            color = "#28a745" if char == 'V' else "#dc3545" if char == 'T' else "#ffc107"
            res += f'<span style="color:{color}; font-weight:bold; margin-right:3px;">{char}</span>'
        return res

    # --- 2. DATABEREGNING (OPTA RESULTATER) ---
    stats = {}
    for _, row in df_opta.iterrows():
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
    next_opponents = {}
    df_upcoming = df_opta[df_opta['MATCH_STATUS'] != 'Played'].copy()
    if not df_upcoming.empty:
        df_upcoming['MATCH_DATE_FULL'] = pd.to_datetime(df_upcoming['MATCH_DATE_FULL'])
        df_upcoming = df_upcoming.sort_values('MATCH_DATE_FULL', ascending=True)

        for uuid in stats.keys():
            future_m = df_upcoming[(df_upcoming['CONTESTANTHOME_OPTAUUID'] == uuid) | (df_upcoming['CONTESTANTAWAY_OPTAUUID'] == uuid)]
            if not future_m.empty:
                row = future_m.iloc[0]
                is_home = row['CONTESTANTHOME_OPTAUUID'] == uuid
                opp_name = row['CONTESTANTAWAY_NAME'] if is_home else row['CONTESTANTHOME_NAME']
                opp_uuid = row['CONTESTANTAWAY_OPTAUUID'] if is_home else row['CONTESTANTHOME_OPTAUUID']
                dato = row['MATCH_DATE_FULL'].strftime('%d/%m')
                logo = get_logo_url(opp_uuid, opp_name)
                next_opponents[uuid] = f'<div style="display:flex;align-items:center;gap:5px;"><img src="{logo}" width="18"><span>{opp_name}</span><span style="color:#888;font-size:11px;">{dato}</span></div>'
            else:
                next_opponents[uuid] = "-"

    # Omdan til DataFrame og Merge med Wyscout stats
    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga['NÆSTE'] = df_liga['UUID'].map(next_opponents)
    df_liga['TEAM_WYID'] = df_liga['UUID'].map(opta_to_wyid)
    
    # Merge Wyscout Advanced Stats (Querien team_stats_full)
    if not df_adv.empty:
        # Vi sikrer os at vi merger på de rigtige kolonnenavne fra din query
        df_liga = df_liga.merge(
            df_adv[['TEAM_WYID', 'PPDA', 'AVERAGE_FORWARD_PASSES', 'AVERAGE_SHOTS']], 
            on='TEAM_WYID', 
            how='left'
        )

    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- 3. GRAF FUNKTION ---
    def draw_h2h_chart(n1, n2, metrics, labels):
        t1 = df_liga[df_liga['HOLD'] == n1].iloc[0].to_dict()
        t2 = df_liga[df_liga['HOLD'] == n2].iloc[0].to_dict()
        fig = go.Figure()
        
        c1 = colors_dict.get(n1, {"primary": "#cc0000"})
        c2 = colors_dict.get(n2, {"primary": "#0056a3"})
        
        for name, data, color in [(n1, t1, c1), (n2, t2, c2)]:
            vals = [data.get(m, 0) for m in metrics]
            fig.add_trace(go.Bar(
                name=name, x=labels, y=vals, 
                marker_color=color["primary"],
                text=[f"{v:.1f}" if isinstance(v, float) else int(v) for v in vals],
                textposition='inside', width=0.25,
                insidetextfont=dict(size=14, color=get_text_color(color["primary"]), family="Arial Black")
            ))

        fig.update_layout(
            barmode='group', bargap=0.3, height=400, margin=dict(t=50, b=40, l=10, r=10),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', showlegend=False,
            yaxis=dict(visible=False), xaxis=dict(tickfont=dict(size=12, family="Arial Black"))
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 4. LAYOUT ---
    st.markdown("""
        <style>
            .league-table { width: 100%; border-collapse: collapse; font-size: 13px; }
            .league-table th { text-align: center; padding: 10px; border-bottom: 2px solid #eee; background: #f8f9fa; }
            .league-table td { text-align: center; padding: 10px; border-bottom: 1px solid #eee; }
            .league-table td:nth-child(3) { text-align: left !important; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        df_disp['FORM'] = df_disp['FORM'].apply(style_form)
        
        # Kolonner til visning (Inkl. de nye Wyscout stats)
        vis_cols = ['#', ' ', 'HOLD', 'K', 'P', 'AVERAGE_SHOTS', 'AVERAGE_FORWARD_PASSES', 'PPDA', 'FORM', 'NÆSTE']
        # Omdøb for pænere header
        df_disp = df_disp.rename(columns={'AVERAGE_SHOTS': 'Skud/K', 'AVERAGE_FORWARD_PASSES': 'Fwd P', 'PPDA': 'PPDA'})
        vis_cols_pretty = ['#', ' ', 'HOLD', 'K', 'P', 'Skud/K', 'Fwd P', 'PPDA', 'FORM', 'NÆSTE']
        
        st.write(df_disp[vis_cols_pretty].to_html(escape=False, index=False, classes='league-table'), unsafe_allow_html=True)

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        st.subheader("Sammenligning")
        s1, s2, s3 = st.tabs(["Resultater", "Offensiv", "Pres & Opbygning"])
        with s1: draw_h2h_chart(team1, team2, ['P', 'V', 'K'], ['Point', 'Sejre', 'Kampe'])
        with s2: draw_h2h_chart(team1, team2, ['AVERAGE_SHOTS', 'M+'], ['Skud pr. kamp', 'Mål total'])
        with s3: draw_h2h_chart(team1, team2, ['PPDA', 'AVERAGE_FORWARD_PASSES'], ['PPDA', 'Forward Passes'])
