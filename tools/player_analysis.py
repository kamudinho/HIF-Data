import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent data fra pakkerne
    df_xg = dp.get("xg_agg")
    df_lb = dp.get("linebreaks")
    df_players = dp.get("players") # Din players.csv fra HIF_load

    if df_xg is None or df_xg.empty or df_players is None:
        st.error("Kunne ikke finde xG-data eller spillerlisten (players.csv).")
        return

    # 2. Mapping: Lav en dictionary {UUID: Navn} fra din players.csv
    # Vi antager at din CSV har 'OPTA_UUID' (eller lign) og 'Navn'
    # Juster kolonnenavnene 'opta_uuid' og 'name' så de matcher din CSV præcis
    name_map = dict(zip(df_players['opta_uuid'], df_players['name']))
    
    # 3. Filtrering & Valg
    # Vi viser kun spillere i dropdown, som vi rent faktisk har data på i xG-tabellen
    available_uuids = df_xg['PLAYER_OPTAUUID'].unique()
    dropdown_options = {uuid: name_map.get(uuid, f"Ukendt ({uuid[:5]})") for uuid in available_uuids}
    
    # Sortér alfabetisk efter navn
    sorted_options = dict(sorted(dropdown_options.items(), key=lambda item: item[1]))

    col_selector, col_info = st.columns([1, 2])
    with col_selector:
        selected_uuid = st.selectbox(
            "Vælg Spiller", 
            options=list(sorted_options.keys()), 
            format_func=lambda x: sorted_options[x]
        )
    
    # 4. Filtrer data for den valgte spiller
    p_xg = df_xg[df_xg['PLAYER_OPTAUUID'] == selected_uuid].copy()
    p_lb = df_lb[df_lb['PLAYER_OPTAUUID'] == selected_uuid].copy() if df_lb is not None else pd.DataFrame()

    st.markdown("---")

    # --- 5. TABS ---
    tab1, tab2, tab3 = st.tabs(["🎯 OFFENSIV IMPACT", "🚀 LINEBREAKS", "📋 RÅ DATA"])

    with tab1:
        # Hovedtal
        m1, m2, m3, m4 = st.columns(4)
        
        # Hjælpefunktion til at hente stats
        def get_stat(df, stat_name):
            val = df[df['STAT_TYPE'] == stat_name]['STAT_VALUE'].sum()
            return float(val)

        total_xg = get_stat(p_xg, 'expectedGoals')
        total_xa = get_stat(p_xg, 'expectedAssists')
        npxg = get_stat(p_xg, 'expectedGoalsNonpenalty')
        mins = get_stat(p_xg, 'minsPlayed')

        m1.metric("Total xG", f"{total_xg:.2f}")
        m2.metric("Non-Penalty xG", f"{npxg:.2f}")
        m3.metric("Total xA", f"{total_xa:.2f}")
        m4.metric("Spilleminutter", int(mins))

        # xG Fordeling (Bar chart)
        xg_cats = ['expectedGoalsHd', 'expectedGoalsOpenplay', 'expectedGoalsSetplay']
        xg_plot_data = p_xg[p_xg['STAT_TYPE'].isin(xg_cats)].groupby('STAT_TYPE')['STAT_VALUE'].sum().reset_index()
        
        if not xg_plot_data.empty:
            fig_xg = px.bar(
                xg_plot_data, x='STAT_TYPE', y='STAT_VALUE',
                title="Hvor kommer chancerne fra?",
                color_discrete_sequence=['#df003b'],
                labels={'STAT_VALUE': 'xG Værdi', 'STAT_TYPE': 'Type'}
            )
            fig_xg.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_xg, use_container_width=True)

    with tab2:
        if not p_lb.empty:
            # Fokus på progression
            lb_types = ['defenceLineBroken', 'midfieldLineBroken', 'attackingLineBroken', 'underPressure']
            lb_data = p_lb[p_lb['STAT_TYPE'].isin(lb_types)]

            # Vi laver et vandret bar chart for at se FH vs SH tydeligt
            fig_lb = px.bar(
                lb_data, y='STAT_TYPE', x=['STAT_FH', 'STAT_SH'],
                orientation='h',
                title="Linjebrud pr. Halvleg",
                color_discrete_map={'STAT_FH': '#b8860b', 'STAT_SH': '#df003b'},
                labels={'value': 'Antal', 'STAT_TYPE': 'Kategori', 'variable': 'Halvleg'}
            )
            st.plotly_chart(fig_lb, use_container_width=True)
        else:
            st.info("Ingen linebreak-data fundet for denne spiller.")

    with tab3:
        # Gør den rå tabel lækker
        st.dataframe(
            p_xg[['MATCH_DATE', 'STAT_TYPE', 'STAT_VALUE']]
            .sort_values('MATCH_DATE', ascending=False),
            use_container_width=True,
            hide_index=True
        )
