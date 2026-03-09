import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING ---
    df_xg = dp.get("opta_expected_goals", pd.DataFrame())
    df_lb = dp.get("opta_player_linebreaks", pd.DataFrame())
    df_shots = dp.get("opta_shotevents", pd.DataFrame()) 
    df_matches = dp.get("opta_matches", pd.DataFrame())
    name_map = dp.get("name_map", {})

    # Tving alle kolonner til STORE bogstaver med det samme
    for df in [df_xg, df_lb, df_shots, df_matches]:
        if not df.empty:
            df.columns = [c.upper() for c in df.columns]

    # --- 2. BYG SPILLER-BASEN (Pivotering) ---
    # Vi laver en liste over alle unikke spillere fra ALLE kilder
    all_players = pd.DataFrame()
    
    if not df_xg.empty:
        xg_piv = df_xg.pivot_table(index=['PLAYER_OPTAUUID', 'CONTESTANT_OPTAUUID'], 
                                  columns='STAT_TYPE', values='STAT_VALUE', aggfunc='sum').reset_index()
        all_players = xg_piv
    
    if not df_lb.empty:
        lb_sum = df_lb.groupby(['PLAYER_OPTAUUID', 'LINEUP_CONTESTANTUUID'])['STAT_VALUE'].sum().reset_index()
        lb_sum.columns = ['PLAYER_OPTAUUID', 'CONTESTANT_OPTAUUID', 'total_linebreaks']
        if all_players.empty:
            all_players = lb_sum
        else:
            all_players = pd.merge(all_players, lb_sum, on=['PLAYER_OPTAUUID', 'CONTESTANT_OPTAUUID'], how='outer')

    if all_players.empty:
        st.warning("⚠️ Ingen data fundet i hverken xG eller Linebreak tabellerne.")
        return

    # Sikring af kolonner og navne
    for col in ['expectedGoals', 'expectedAssists', 'touches', 'total_linebreaks']:
        if col not in all_players.columns:
            all_players[col] = 0.0

    all_players['PLAYER_OPTAUUID'] = all_players['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip()
    all_players['NAVN'] = all_players['PLAYER_OPTAUUID'].map(name_map).fillna(all_players['PLAYER_OPTAUUID'])
    all_players['SELECT_NAME'] = all_players['NAVN']

    # --- 3. TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["HOLDOVERSIGT", "SPILLERPERFORMANCE", "LINEBREAKS"])

    with tab_squad:
        # Oversigt der nu også viser linebreaks
        display_df = all_players[['NAVN', 'total_linebreaks', 'expectedGoals', 'expectedAssists', 'touches']].sort_values('total_linebreaks', ascending=False)
        st.dataframe(display_df.style.format({'expectedGoals': '{:.2f}', 'expectedAssists': '{:.2f}'}), use_container_width=True, hide_index=True)

    with tab_single:
        all_names = sorted(all_players['SELECT_NAME'].unique())
        selected_display = st.selectbox("Vælg spiller", options=all_names, key="ps_select")
        p_row = all_players[all_players['SELECT_NAME'] == selected_display].iloc[0]
        selected_uuid = p_row['PLAYER_OPTAUUID']

        # Metrics række
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Linebreaks I alt", int(p_row['total_linebreaks']))
        m2.metric("xG", f"{p_row['expectedGoals']:.2f}")
        m3.metric("xA", f"{p_row['expectedAssists']:.2f}")
        m4.metric("Touches", int(p_row['touches']))

        # Bar Chart til sammenligning
        metric_options = {'total_linebreaks': 'Total Linebreaks', 'expectedGoals': 'xG', 'touches': 'Touches'}
        col_t, col_d = st.columns([2, 1])
        with col_d:
            sel_metric = st.selectbox("Kategori", options=list(metric_options.keys()), format_func=lambda x: metric_options[x], label_visibility="collapsed")
        
        chart_data = all_players.sort_values(sel_metric, ascending=False).head(10).copy()
        chart_data['Farve'] = chart_data['SELECT_NAME'].apply(lambda x: '#df003b' if x == selected_display else '#D3D3D3')
        
        fig = px.bar(chart_data, x=sel_metric, y='NAVN', orientation='h', color='Farve', color_discrete_map="identity")
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with tab_lb:
        if not df_lb.empty:
            p_lb_data = df_lb[df_lb['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip() == selected_uuid].copy()
            if not p_lb_data.empty:
                st.subheader(f"Linebreak Detaljer: {p_row['NAVN']}")
                
                c1, c2 = st.columns([2, 1])
                with c1:
                    chart_df = p_lb_data[~p_lb_data['STAT_TYPE'].str.contains('percentage', case=False)].sort_values('STAT_VALUE', ascending=True)
                    fig_lb = px.bar(chart_df, x='STAT_VALUE', y='STAT_TYPE', orientation='h', color_discrete_sequence=['#df003b'])
                    st.plotly_chart(fig_lb, use_container_width=True)
                with c2:
                    st.dataframe(p_lb_data[['STAT_TYPE', 'STAT_VALUE', 'STAT_FH', 'STAT_SH']], use_container_width=True, hide_index=True)
            else:
                st.info(f"Ingen linebreaks fundet for denne spiller.")
        else:
            st.error("Linebreak-tabellen er tom i Snowflake.")
