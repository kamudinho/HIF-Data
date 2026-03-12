import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.utils.team_mapping import TEAMS, TEAM_COLORS
from data.data_load import _get_snowflake_conn

def vis_side(df_raw=None):
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet.")
        return

    dp = st.session_state["dp"]
    colors_dict = dp.get("config", {}).get("colors", TEAM_COLORS)
    logo_map = dp.get("logo_map", {})
    df_opta = dp.get("opta", {}).get("matches", pd.DataFrame())
    
    conn = _get_snowflake_conn()
    DB = "KLUB_HVIDOVREIF.AXIS"

    if df_opta.empty:
        st.warning("Ingen kampdata fundet.")
        return

    # --- 1. HJÆLPEFUNKTIONER ---
    def get_logo_url(opta_uuid):
        wy_id = next((info.get('team_wyid') for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), None)
        if wy_id and wy_id in logo_map:
            return logo_map[wy_id]
        return next((info['logo'] for name, info in TEAMS.items() if info.get('opta_uuid') == opta_uuid), "")

    def get_logo_html(uuid):
        url = get_logo_url(uuid)
        return f'<img src="{url}" width="20">' if url else ""

    def get_text_color(hex_color):
        if not hex_color: return "white"
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (r * 0.299 + g * 0.587 + b * 0.114)
        return "black" if luminance > 165 else "white"

    # --- 2. DATABEREGNING (OPTA LIGATABEL) ---
    stats = {}
    for _, row in df_opta.iterrows():
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        for uuid, name in [(h_uuid, row['CONTESTANTHOME_NAME']), (a_uuid, row['CONTESTANTAWAY_NAME'])]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0, 'FORM': "", 'UUID': uuid}
        
        if row['MATCH_STATUS'] == 'Played':
            h_g = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
            a_g = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
            winner = str(row['WINNER']).lower()
            s_h, s_a = stats[h_uuid], stats[a_uuid]
            s_h['K'] += 1; s_a['K'] += 1
            s_h['M+'] += h_g; s_h['M-'] += a_g; s_a['M+'] += a_g; s_a['M-'] += h_g
            if winner == 'home':
                s_h['V'] += 1; s_h['P'] += 3; s_a['T'] += 1
            elif winner == 'away':
                s_a['V'] += 1; s_a['P'] += 3; s_h['T'] += 1
            else:
                s_h['U'] += 1; s_h['P'] += 1; s_a['U'] += 1; s_a['P'] += 1

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- 3. WYSCOUT DATA ---
    @st.cache_data(ttl=600)
    def get_wyscout_direct():
        if not conn: return pd.DataFrame()
        query = f"""
        SELECT t.TEAMNAME, 
               adv.XG, adv.SHOTS, adv.GOALS, adv.XGPERSHOT, 
               adv.AVGDISTANCE, adv.SHOTSONTARGET, adv.SHOTSBLOCKED, 
               adv.SHOTSOUTSIDEBOX, adv.SHOTSFROMBOX, adv.SHOTSFROMBOXONTARGET, 
               adv.SHOTSFROMDANGERZONE,
               md.INTERCEPTIONS, md.TACKLES, md.CLEARANCES, md.PPDA,
               mp.PASSES, mp.PASSESSUCCESSFUL, mp.CROSSESTOTAL, mp.FORWARDPASSES, 
               mp.PROGRESSIVEPASSES, mp.PASSTOFINALTHIRDS, mp.AVGPASSLENGTH, mp.MATCHTEMPO
        FROM {DB}.WYSCOUT_TEAMMATCHES tm 
        JOIN {DB}.WYSCOUT_TEAMS t ON tm.TEAM_WYID = t.TEAM_WYID 
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_GENERAL adv ON tm.MATCH_WYID = adv.MATCH_WYID AND tm.TEAM_WYID = adv.TEAM_WYID 
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_DEFENCE md ON tm.MATCH_WYID = md.MATCH_WYID AND tm.TEAM_WYID = md.TEAM_WYID 
        LEFT JOIN {DB}.WYSCOUT_MATCHADVANCEDSTATS_PASSES mp ON tm.MATCH_WYID = mp.MATCH_WYID AND tm.TEAM_WYID = mp.TEAM_WYID 
        WHERE tm.COMPETITION_WYID = 328
        """
        return conn.query(query)

    df_wy_raw = get_wyscout_direct()

    # --- 4. GRAF FUNKTION (RETTET: NU MED BÅDE LOGOER OG SYNLIGE LABELS) ---
    # --- 4. GRAF FUNKTION (OPDATERET MED ROTEREDE LABELS OG AUTOMARGIN) ---
    def draw_h2h_chart_combined(team1, team2, metrics, labels, df_source, chart_key):
        d1 = df_source[df_source['TEAMNAME'].str.contains(team1, case=False, na=False)]
        d2 = df_source[df_source['TEAMNAME'].str.contains(team2, case=False, na=False)]
        
        if d1.empty or d2.empty:
            st.info("Ingen data fundet.")
            return

        v1 = [d1.iloc[0].get(m, 0) for m in metrics]
        v2 = [d2.iloc[0].get(m, 0) for m in metrics]
        
        u1 = df_liga[df_liga['HOLD'] == team1]['UUID'].values[0]
        u2 = df_liga[df_liga['HOLD'] == team2]['UUID'].values[0]
        l1, l2 = get_logo_url(u1), get_logo_url(u2)
        
        c1 = colors_dict.get(team1, {"primary": "#df003b"})
        c2 = colors_dict.get(team2, {"primary": "#0056a3"})

        fig = go.Figure()
        x_indices = list(range(len(labels)))
        
        # Hold 1 Søjler
        fig.add_trace(go.Bar(
            name=team1, x=x_indices, y=v1, marker_color=c1["primary"], 
            text=[f"{x:.2f}" for x in v1], textposition='inside', 
            insidetextfont=dict(size=14, family="Arial Black", color=get_text_color(c1["primary"])),
            offsetgroup=1
        ))
        
        # Hold 2 Søjler
        fig.add_trace(go.Bar(
            name=team2, x=x_indices, y=v2, marker_color=c2["primary"], 
            text=[f"{x:.2f}" for x in v2], textposition='inside', 
            insidetextfont=dict(size=14, family="Arial Black", color=get_text_color(c2["primary"])),
            offsetgroup=2
        ))

        # LOGOER
        for i in range(len(labels)):
            if l1:
                fig.add_layout_image(dict(
                    source=l1, xref="x", yref="paper",
                    x=i - 0.18, y=1.05, sizex=0.18, sizey=0.18,
                    xanchor="center", yanchor="bottom", opacity=1, layer="above"
                ))
            if l2:
                fig.add_layout_image(dict(
                    source=l2, xref="x", yref="paper",
                    x=i + 0.18, y=1.05, sizex=0.18, sizey=0.18,
                    xanchor="center", yanchor="bottom", opacity=1, layer="above"
                ))

        fig.update_layout(
            barmode='group',
            height=500, # Vi sætter højden lidt op for at give plads
            margin=dict(t=100, b=150, l=20, r=20), # Markant mere plads i bunden (150px)
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            yaxis=dict(visible=False, fixedrange=True, range=[0, max(max(v1), max(v2)) * 1.4]),
            xaxis=dict(
                type='category',
                showgrid=False,
                tickmode='array',
                tickvals=x_indices,
                ticktext=labels,
                # VI TVINGER SORT FARVE HER:
                tickfont=dict(size=11, family="Arial", color="#333333"), 
                tickangle=-0, # Drej dem så de ikke overlapper
                automargin=True, # Bed Plotly om selv at finde plads
                fixedrange=True,
                anchor="y",
                side="bottom"
            )
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=chart_key) 
        
    # --- 5. LAYOUT ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        # --- LIGATABEL ---
        df_disp = df_liga.copy()
        df_disp.insert(1, ' ', [get_logo_html(u) for u in df_disp['UUID']])
        st.write(df_disp[['#', ' ', 'HOLD', 'K', 'V', 'U', 'T', 'MD', 'P']].to_html(escape=False, index=False), unsafe_allow_html=True)
        
        # --- NÆSTE MODSTANDER (KUN TEKST) ---
        st.markdown("---")
        
        # Find Hvidovres Opta UUID
        hif_opta_uuid = next((info.get('opta_uuid') for name, info in TEAMS.items() if info.get('team_wyid') == 7490), None)
        
        if hif_opta_uuid:
            next_m = df_opta[
                (df_opta['MATCH_STATUS'] == 'Fixture') & 
                ((df_opta['CONTESTANTHOME_OPTAUUID'] == hif_opta_uuid) | 
                 (df_opta['CONTESTANTAWAY_OPTAUUID'] == hif_opta_uuid))
            ].sort_values(by='TIME_UTC').head(1)

            if not next_m.empty:
                m = next_m.iloc[0]
                is_home = m['CONTESTANTHOME_OPTAUUID'] == hif_opta_uuid
                dato = pd.to_datetime(m['TIME_UTC']).strftime('%d. %b - kl. %H:%M')
                
                home_team = m['CONTESTANTHOME_NAME'].upper()
                away_team = m['CONTESTANTAWAY_NAME'].upper()
                spillested = "Hjemme" if is_home else "Ude"

                # Rent tekst-layout
                st.markdown(f"### NÆSTE KAMP: {home_team} vs {away_team}")
                st.markdown(f"**Dato:** {dato}  \n**Lokation:** {spillested}")
            else:
                st.write("INGEN KOMMENDE KAMPE PLANLAGT")
    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        if not df_wy_raw.empty:
            df_wy_raw.columns = [col.upper() for col in df_wy_raw.columns]
            df_agg = df_wy_raw.groupby('TEAMNAME').mean(numeric_only=True).reset_index()
            
            # Nye organiserede faner
            sub_tabs = st.tabs(["Generelt", "xG Stats", "Afslutninger", "Defensivt", "Spilopbygning"])
            
            # 1. GENERELT (Overblik med blandede volumen-stats)
            with sub_tabs[0]:
                metrics = ['SHOTS', 'GOALS', 'PPDA', 'MATCHTEMPO']
                labels = ['Skud', 'Mål', 'PPDA', 'Match Tempo']
                draw_h2h_chart_combined(team1, team2, metrics, labels, df_agg, "gen_chart")
            
            # 2. xG STATS (Egen fane pga. små decimalværdier)
            with sub_tabs[1]:
                metrics = ['XG', 'XGPERSHOT']
                labels = ['Total xG', 'xG pr. skud']
                draw_h2h_chart_combined(team1, team2, metrics, labels, df_agg, "xg_chart")
            
            # 3. AFSLUTNINGER (Specifikke skud-typer)
            with sub_tabs[2]:
                metrics = [
                    'SHOTSONTARGET', 'SHOTSBLOCKED', 'SHOTSOUTSIDEBOX', 
                    'SHOTSFROMBOX', 'SHOTSFROMBOXONTARGET', 'SHOTSFROMDANGERZONE'
                ]
                labels = [
                    'På mål', 'Blokeret', 'Udenfor felt', 
                    'I feltet', 'I felt på mål', 'Danger Zone'
                ]
                draw_h2h_chart_combined(team1, team2, metrics, labels, df_agg, "shot_chart")
            
            # 4. DEFENSIVT (Forsvars-kategorier)
            with sub_tabs[3]:
                metrics = ['INTERCEPTIONS', 'TACKLES', 'CLEARANCES']
                labels = ['Interceptions', 'Tacklinger', 'Clearinger']
                draw_h2h_chart_combined(team1, team2, metrics, labels, df_agg, "def_chart")
            
            # 5. SPILOPBYGNING (Afleveringer og indlæg)
            with sub_tabs[4]:
                metrics = [
                    'PASSES', 'CROSSESTOTAL', 
                    'FORWARDPASSES', 'PROGRESSIVEPASSES', 'PASSTOFINALTHIRDS'
                ]
                labels = [
                    'Afleveringer', 'Indlæg', 
                    'Fremadrettede', 'Progressive', 'Til sidste 1/3'
                ]
                draw_h2h_chart_combined(team1, team2, metrics, labels, df_agg, "pass_chart")
