import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING ---
    df_xg = dp.get("xg_agg", pd.DataFrame())
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    df_shots = dp.get("playerstats", pd.DataFrame()) # Bruges til Skud & DZ
    df_matches = dp.get("matches", pd.DataFrame())
    name_map = dp.get("name_map", {})
    
    saeson_f = st.session_state.get('saeson_f', 'Valgt Sæson')

    if df_xg.empty:
        st.warning("⚠️ Ingen data fundet.")
        return

    # --- 2. DATA CLEANING & HOLD-MAPPING ---
    df_xg.columns = [c.upper() for c in df_xg.columns]
    player_col = 'PLAYER_OPTAUUID'
    team_col = 'CONTESTANT_OPTAUUID'
    
    team_map = {}
    if not df_matches.empty:
        df_matches.columns = [c.upper() for c in df_matches.columns]
        for _, row in df_matches.iterrows():
            team_map[row['CONTESTANTHOME_OPTAUUID']] = row['CONTESTANTHOME_NAME']
            team_map[row['CONTESTANTAWAY_OPTAUUID']] = row['CONTESTANTAWAY_NAME']

    # --- 3. PIVOTERING & METRIC BEREGNING ---
    # Grund-stats (xG, xA, Touches)
    pivot_stats = df_xg.pivot_table(
        index=[player_col, team_col], 
        columns='STAT_TYPE', 
        values='STAT_VALUE',
        aggfunc='sum'
    ).fillna(0).reset_index()

    # Sikring af de 5 kategorier
    for col in ['expectedGoals', 'expectedAssists', 'touches']:
        if col not in pivot_stats.columns:
            pivot_stats[col] = 0.0

    # Beregn Skud og Skud i DZ fra df_shots
    shot_counts = []
    dz_counts = []
    
    if not df_shots.empty:
        df_shots.columns = [c.upper() for c in df_shots.columns]
        for _, row in pivot_stats.iterrows():
            p_uuid = str(row[player_col]).lower()
            p_shots = df_shots[df_shots[player_col].astype(str).str.lower() == p_uuid]
            
            shot_counts.append(len(p_shots))
            if 'EVENT_X' in p_shots.columns and 'EVENT_Y' in p_shots.columns:
                dz = p_shots[(p_shots['EVENT_X'] >= 88.5) & (p_shots['EVENT_Y'].between(37, 63))]
                dz_counts.append(len(dz))
            else:
                dz_counts.append(0)
    else:
        shot_counts = [0] * len(pivot_stats)
        dz_counts = [0] * len(pivot_stats)

    pivot_stats['Skud'] = shot_counts
    pivot_stats['Skud i DZ'] = dz_counts

    # Navne-mapping
    pivot_stats[player_col] = pivot_stats[player_col].astype(str).str.lower()
    pivot_stats['NAVN'] = pivot_stats[player_col].map(name_map).fillna(pivot_stats[player_col])
    pivot_stats['SELECT_NAME'] = pivot_stats['NAVN']

    # --- 4. TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["HOLDOVERSIGT", "SPILLERPERFORMANCE", "LINEBREAKS"])

    with tab_squad:        
        # Vi definerer de kolonner vi vil vise og sorterer efter xG som standard
        display_df = pivot_stats[['NAVN', 'expectedGoals', 'expectedAssists', 'Skud', 'Skud i DZ', 'touches']].copy()
        display_df = display_df.sort_values('expectedGoals', ascending=False)
        
        # Dynamisk højde: (antal rækker * 35 pixels) + 38 pixels til headeren
        # Vi sætter en max-højde på 800 for at undgå at siden bliver uendelig lang
        calc_height = min((len(display_df) * 35) + 38, 800)

        st.dataframe(
            display_df.style.format({
                'expectedGoals': '{:.2f}', 
                'expectedAssists': '{:.2f}',
                'Skud': '{:,.0f}',
                'Skud i DZ': '{:,.0f}',
                'touches': '{:,.0f}'
            }), 
            use_container_width=True, 
            height=calc_height, 
            hide_index=True
        )

    with tab_single:
        # 1. Spiller-vælger (Top-sektion)
        all_names = sorted(pivot_stats['SELECT_NAME'].unique())
        selected_display = st.selectbox("Vælg spiller for detaljer", options=all_names, key="player_select")
        p_row = pivot_stats[pivot_stats['SELECT_NAME'] == selected_display].iloc[0]
        selected_uuid = p_row[player_col]

        # 2. Metrics Række
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("xG", f"{p_row['expectedGoals']:.2f}")
        m2.metric("xA", f"{p_row['expectedAssists']:.2f}")
        m3.metric("Skud", int(p_row['Skud']))
        m4.metric("Skud i DZ", int(p_row['Skud i DZ']))
        m5.metric("Touches", int(p_row['touches']))
        st.write("---")

        # 3. Bar Chart Overskrift og Dropdown på samme linje
        metric_options = {
            'expectedGoals': 'Expected Goals (xG)',
            'expectedAssists': 'Expected Assists (xA)',
            'Skud': 'Antal Skud',
            'Skud i DZ': 'Skud i Dangerzone',
            'touches': 'Touches (Berøringer)'
        }

        col_title, col_dropdown = st.columns([2, 1])
        
        with col_title:
            # Vi definerer titlen her, men viser den i selve figuren senere
            current_metric_name = metric_options[st.session_state.get('selected_metric', 'expectedGoals')]
            st.caption(f"Top 10: {current_metric_name}")

        with col_dropdown:
            selected_metric_key = st.selectbox(
                "Vælg kategori", # Denne label kan skjules med label_visibility hvis ønsket
                options=list(metric_options.keys()), 
                format_func=lambda x: metric_options[x],
                key='selected_metric',
                label_visibility="collapsed" 
            )

        # --- Bar Chart Sektion ---
        chart_data = pivot_stats.sort_values(selected_metric_key, ascending=False).head(10).copy()
        
        # Markér valgt spiller
        chart_data['Farve'] = chart_data['SELECT_NAME'].apply(
            lambda x: '#df003b' if x == selected_display else '#D3D3D3'
        )

        fig = px.bar(chart_data, 
                     x=selected_metric_key, 
                     y='NAVN', 
                     orientation='h',
                     labels={selected_metric_key: metric_options[selected_metric_key], 'NAVN': 'Spiller'},
                     color='Farve',
                     color_discrete_map="identity",
                     text_auto='.2f' if 'expected' in selected_metric_key else True)
        
        fig.update_layout(
            yaxis={'categoryorder':'total ascending'}, 
            showlegend=False,
            margin=dict(l=20, r=20, t=10, b=20), # Mindre margin i toppen da vi har subheader
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

    with tab_lb:
        # (Din eksisterende linebreak logik her...)
        st.info("Linebreak data vises her.")
