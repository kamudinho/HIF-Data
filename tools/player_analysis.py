import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent data fra pakken
    df_xg = dp.get("xg_agg")
    df_lb = dp.get("linebreaks")
    name_map = dp.get("name_map", {})

    if df_xg is None or df_xg.empty:
        st.warning("⚠️ Ingen xG-data fundet i Snowflake for den valgte periode.")
        return

    # 2. Forberedelse af data og sikring af navne
    df_working = df_xg.copy()
    df_working['STAT_VALUE'] = pd.to_numeric(df_working['STAT_VALUE'], errors='coerce').fillna(0)
    
    # Tving ID til string for fejlfrit match med name_map
    df_working['PLAYER_OPTAUUID'] = df_working['PLAYER_OPTAUUID'].astype(str).str.strip()
    
    # Pivotering: Hver spiller får én række
    pivot_stats = df_working.pivot_table(
        index='PLAYER_OPTAUUID', 
        columns='STAT_TYPE', 
        values='STAT_VALUE', 
        aggfunc='sum'
    ).fillna(0).reset_index()

    # Påfør navne fra name_map efter pivotering
    pivot_stats['NAVN'] = pivot_stats['PLAYER_OPTAUUID'].map(name_map)
    
    # Håndter spillere der ikke findes i CSV (modstandere/nye spillere)
    pivot_stats['NAVN'] = pivot_stats['NAVN'].fillna(pivot_stats['PLAYER_OPTAUUID'].apply(lambda x: f"Ukendt ({x[:5]})"))

    # Beregn xG pr. 90 min (hvis data er til stede)
    if 'minsPlayed' in pivot_stats.columns and 'expectedGoals' in pivot_stats.columns:
        # Undgå division med nul
        pivot_stats['xG_90'] = (pivot_stats['expectedGoals'] / pivot_stats.apply(lambda r: max(r['minsPlayed'], 1), axis=1) * 90)
    else:
        pivot_stats['xG_90'] = 0

    # --- 3. VISNING I TABS ---
    tab_squad, tab_single, tab_lb = st.tabs([
        "📊 TRUP OVERSIGT", 
        "🎯 INDIVIDUEL ANALYSE", 
        "🚀 LINEBREAKS"
    ])

    with tab_squad:
        st.subheader("Leaderboard: Sæsonstatistik")
        
        # Kolonner vi vil vise
        display_cols = ['NAVN', 'minsPlayed', 'expectedGoals', 'expectedAssists', 'expectedGoalsNonpenalty', 'xG_90']
        final_cols = [c for c in display_cols if c in pivot_stats.columns]
        
        df_table = pivot_stats[final_cols].sort_values('expectedGoals', ascending=False)

        st.dataframe(
            df_table,
            column_config={
                "NAVN": st.column_config.TextColumn("Spiller"),
                "minsPlayed": st.column_config.NumberColumn("Minutter", format="%d"),
                "expectedGoals": st.column_config.NumberColumn("Total xG", format="%.2f"),
                "expectedAssists": st.column_config.NumberColumn("Total xA", format="%.2f"),
                "expectedGoalsNonpenalty": st.column_config.NumberColumn("npxG", format="%.2f"),
                "xG_90": st.column_config.NumberColumn("xG/90", format="%.2f")
            },
            use_container_width=True,
            hide_index=True
        )

    with tab_single:
        # Dropdown til enkeltspiller
        available_uuids = sorted(pivot_stats['PLAYER_OPTAUUID'].unique(), 
                                key=lambda x: pivot_stats[pivot_stats['PLAYER_OPTAUUID'] == x]['NAVN'].values[0])
        
        col_sel, _ = st.columns([1, 2])
        with col_sel:
            selected_uuid = st.selectbox(
                "Vælg Spiller", 
                options=available_uuids, 
                format_func=lambda x: pivot_stats[pivot_stats['PLAYER_OPTAUUID'] == x]['NAVN'].values[0]
            )

        # Metrics for valgte spiller
        p_xg = df_working[df_working['PLAYER_OPTAUUID'] == selected_uuid]
        
        m1, m2, m3, m4 = st.columns(4)
        def get_v(stat): return p_xg[p_xg['STAT_TYPE'] == stat]['STAT_VALUE'].sum()

        m1.metric("Total xG", f"{get_v('expectedGoals'):.2f}")
        m2.metric("Non-Penalty xG", f"{get_v('expectedGoalsNonpenalty'):.2f}")
        m3.metric("Total xA", f"{get_v('expectedAssists'):.2f}")
        m4.metric("Minutter", int(get_v('minsPlayed')))

        # xG Fordeling Graf
        xg_cats = ['expectedGoalsHd', 'expectedGoalsOpenplay', 'expectedGoalsSetplay']
        xg_plot = p_xg[p_xg['STAT_TYPE'].isin(xg_cats)].groupby('STAT_TYPE')['STAT_VALUE'].sum().reset_index()
        
        if not xg_plot.empty and xg_plot['STAT_VALUE'].sum() > 0:
            fig_xg = px.bar(xg_plot, x='STAT_TYPE', y='STAT_VALUE', 
                            title="xG Fordeling", 
                            color_discrete_sequence=['#df003b'])
            st.plotly_chart(fig_xg, use_container_width=True)

    with tab_lb:
        if df_lb is not None and not df_lb.empty:
            # Tving ID til string her også for match
            df_lb['PLAYER_OPTAUUID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.strip()
            p_lb = df_lb[df_lb['PLAYER_OPTAUUID'] == selected_uuid].copy()
            
            if not p_lb.empty:
                for col in ['STAT_FH', 'STAT_SH']:
                    p_lb[col] = pd.to_numeric(p_lb[col], errors='coerce').fillna(0)
                
                lb_types = ['defenceLineBroken', 'midfieldLineBroken', 'attackingLineBroken']
                lb_data = p_lb[p_lb['STAT_TYPE'].isin(lb_types)]

                fig_lb = px.bar(lb_data, y='STAT_TYPE', x=['STAT_FH', 'STAT_SH'],
                                orientation='h', title="Linjebrud pr. Halvleg",
                                color_discrete_map={'STAT_FH': '#b8860b', 'STAT_SH': '#df003b'})
                st.plotly_chart(fig_lb, use_container_width=True)
            else:
                st.info("Ingen linebreak-data fundet for denne spiller.")
