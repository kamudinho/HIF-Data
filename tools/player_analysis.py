import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):    
    # 1. Datatjek
    df_xg = dp.get("xg_agg")        # Fra OPTA_MATCHEXPECTEDGOALS
    df_lb = dp.get("linebreaks")    # Fra OPTA_PLAYERLINEBREAKINGPASSAGGREGATES
    
    if df_xg is None or df_xg.empty:
        st.warning("Ingen xG-data fundet for spillerne.")
        return

    # 2. Vælg Spiller (Filtrering)
    all_players = sorted(df_xg['PLAYER_OPTAUUID'].unique())
    selected_player = st.selectbox("Vælg Spiller", all_players)

    # Filtrer data for den valgte spiller
    p_xg = df_xg[df_xg['PLAYER_OPTAUUID'] == selected_player]
    p_lb = df_lb[df_lb['PLAYER_OPTAUUID'] == selected_player] if df_lb is not None else pd.DataFrame()

    # --- 3. TABS OVERSIGT ---
    tab1, tab2, tab3 = st.tabs(["🎯 Afslutning & xG", "🚀 Progression (Linebreaks)", "📊 Rå Statistik"])

    with tab1:
        st.markdown("### Forventede Mål (xG) & Assists (xA)")
        col1, col2, col3 = st.columns(3)
        
        # Beregn totaler (Sørg for at STAT_VALUE er numerisk i din load-fil)
        total_xg = p_xg[p_xg['STAT_TYPE'] == 'expectedGoals']['STAT_VALUE'].sum()
        total_xa = p_xg[p_xg['STAT_TYPE'] == 'expectedAssists']['STAT_VALUE'].sum()
        mins = p_xg[p_xg['STAT_TYPE'] == 'minsPlayed']['STAT_VALUE'].sum()

        col1.metric("Total xG", f"{total_xg:.2f}")
        col2.metric("Total xA", f"{total_xa:.2f}")
        col3.metric("Minutter", f"{int(mins)}")

        # Visualisering af xG kilder (Open Play vs Set Play)
        xg_types = p_xg[p_xg['STAT_TYPE'].str.contains('expectedGoals', na=False)]
        if not xg_types.empty:
            fig_xg = px.bar(xg_types, x='STAT_TYPE', y='STAT_VALUE', 
                            title="xG Fordeling", color_discrete_sequence=['#df003b'])
            st.plotly_chart(fig_xg, use_container_width=True)

    with tab2:
        st.markdown("### Linebreaking Passes")
        if not p_lb.empty:
            # Fokus på de vigtigste gennembrud
            vigtige_stats = ['defenceLineBroken', 'midfieldLineBroken', 'finalThirdEntries', 'underPressure']
            lb_summary = p_lb[p_lb['STAT_TYPE'].isin(vigtige_stats)]
            
            # Sammenlign 1. vs 2. halvleg
            fig_lb = px.bar(lb_summary, x='STAT_TYPE', y=['STAT_FH', 'STAT_SH'], 
                            barmode='group', title="Linjebrud: 1. vs 2. Halvleg",
                            labels={'value': 'Antal', 'variable': 'Halvleg'},
                            color_discrete_map={'STAT_FH': '#b8860b', 'STAT_SH': '#df003b'})
            st.plotly_chart(fig_lb, use_container_width=True)
            
            st.info("💡 'defenceLineBroken' under pres er en nøgleindikator for gennembrudskraft.")
        else:
            st.info("Ingen linebreak-data for denne spiller.")

    with tab3:
        st.markdown("### Komplet Datavisning")
        st.dataframe(p_xg[['MATCH_DATE', 'STAT_TYPE', 'STAT_VALUE']].sort_values('MATCH_DATE', ascending=False), use_container_width=True)
