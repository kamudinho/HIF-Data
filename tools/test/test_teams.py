import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def vis_side(dp):
    if not dp:
        st.error("Data pakken 'dp' mangler.")
        return

    # --- 1. DATAUDTRÆK ---
    # Opta (Matches)
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame())
    
    # Wyscout (Fra dine SQL queries i HIF_load / analyse_load)
    # Vi forventer disse er indlæst via din Snowflake-forbindelse
    df_wy_stats = dp.get("wyscout", {}).get("player_stats_total", pd.DataFrame())
    df_wy_players = dp.get("wyscout", {}).get("wyscout_players", pd.DataFrame())

    if df_matches.empty:
        st.warning("Ingen Opta data tilgængelig.")
        return

    # --- 2. BEREGNING AF LIGATABEL (OPTA) ---
    stats = {}
    for _, row in df_matches.iterrows():
        if row['MATCH_STATUS'] != 'Played':
            continue
            
        h_uuid, a_uuid = row['CONTESTANTHOME_OPTAUUID'], row['CONTESTANTAWAY_OPTAUUID']
        h_name, a_name = row['CONTESTANTHOME_NAME'], row['CONTESTANTAWAY_NAME']
        h_g = int(row['TOTAL_HOME_SCORE']) if pd.notnull(row['TOTAL_HOME_SCORE']) else 0
        a_g = int(row['TOTAL_AWAY_SCORE']) if pd.notnull(row['TOTAL_AWAY_SCORE']) else 0
        winner = str(row['WINNER']).lower()

        for uuid, name in [(h_uuid, h_name), (a_uuid, a_name)]:
            if uuid not in stats:
                stats[uuid] = {'HOLD': name, 'K': 0, 'V': 0, 'U': 0, 'T': 0, 'M+': 0, 'M-': 0, 'P': 0}

        s_h, s_a = stats[h_uuid], stats[a_uuid]
        s_h['K'] += 1; s_a['K'] += 1
        s_h['M+'] += h_g; s_h['M-'] += a_g
        s_a['M+'] += a_g; s_a['M-'] += h_g

        if winner == 'home':
            s_h['V'] += 1; s_h['P'] += 3
            s_a['T'] += 1
        elif winner == 'away':
            s_a['V'] += 1; s_a['P'] += 3
            s_h['T'] += 1
        else:
            s_h['U'] += 1; s_h['P'] += 1
            s_a['U'] += 1; s_a['P'] += 1

    df_liga = pd.DataFrame(stats.values())
    df_liga['MD'] = df_liga['M+'] - df_liga['M-']
    df_liga = df_liga.sort_values(by=['P', 'MD', 'M+'], ascending=False).reset_index(drop=True)
    df_liga.insert(0, '#', df_liga.index + 1)

    # --- 3. WYSCOUT AGGREGERING (KLARGØRING) ---
    df_team_totals = pd.DataFrame()
    if not df_wy_stats.empty and not df_wy_players.empty:
        # Matcher spillernes performance med deres holdnavne
        df_merged = pd.merge(
            df_wy_stats, 
            df_wy_players[['PLAYER_WYID', 'TEAMNAME']], 
            on='PLAYER_WYID', 
            how='inner'
        )
        # Lægger alle spiller-stats sammen pr. hold
        df_team_totals = df_merged.groupby('TEAMNAME').sum(numeric_only=True).reset_index()

    # --- 4. VISNING ---
    t_liga, t_h2h = st.tabs(["Ligaoversigt", "Head-to-head"])

    with t_liga:
        # Ren tabel uden HTML/Ikoner
        st.dataframe(
            df_liga[['#', 'HOLD', 'K', 'V', 'U', 'T', 'M+', 'M-', 'MD', 'P']], 
            use_container_width=True, 
            hide_index=True
        )

    with t_h2h:
        h_list = sorted(df_liga['HOLD'].tolist())
        c1, c2 = st.columns(2)
        team1 = c1.selectbox("Hold 1", h_list, index=h_list.index("Hvidovre") if "Hvidovre" in h_list else 0)
        team2 = c2.selectbox("Hold 2", [h for h in h_list if h != team1])

        if not df_team_totals.empty:
            # Find data for valgte hold (case-insensitive match for at ramme f.eks. 'Hvidovre IF')
            d1 = df_team_totals[df_team_totals['TEAMNAME'].str.contains(team1, case=False, na=False)]
            d2 = df_team_totals[df_team_totals['TEAMNAME'].str.contains(team2, case=False, na=False)]

            if not d1.empty and not d2.empty:
                # Vi bruger dine præcise SQL kolonnenavne her
                metrics = ['XGSHOT', 'PROGRESSIVERUN', 'TOUCHINBOX', 'RECOVERIES']
                labels = ['xG Total', 'Progressive Løb', 'Felt-berør.', 'Genvindinger']
                
                y1 = d1.iloc[0][metrics].tolist()
                y2 = d2.iloc[0][metrics].tolist()

                fig = go.Figure()
                fig.add_trace(go.Bar(name=team1, x=labels, y=y1, marker_color="#df003b"))
                fig.add_trace(go.Bar(name=team2, x=labels, y=y2, marker_color="#0056a3"))
                
                fig.update_layout(
                    barmode='group', 
                    height=400, 
                    margin=dict(t=20, b=20, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(f"Kunne ikke finde Wyscout-data for {team1} eller {team2}.")
        else:
            st.warning("Wyscout data (player_stats_total) er ikke tilgængelig.")
