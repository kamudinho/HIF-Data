import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent data
    df_xg = dp.get("xg_agg")
    df_lb = dp.get("linebreaks")
    # Vi henter name_map og tvinger alle nøgler til at være strings (fjern usynlige tegn)
    raw_name_map = dp.get("name_map", {})
    name_map = {str(k).strip(): str(v) for k, v in raw_name_map.items()}

    if df_xg is None or df_xg.empty:
        st.warning("⚠️ Ingen xG-data fundet.")
        return

    # 2. Forberedelse af data
    df_working = df_xg.copy()
    df_working['STAT_VALUE'] = pd.to_numeric(df_working['STAT_VALUE'], errors='coerce').fillna(0)
    
    # 3. Pivotering
    # Vi bruger 'PLAYER_OPTAUUID' som index og tvinger det bagefter til kolonne
    pivot_stats = df_working.pivot_table(
        index='PLAYER_OPTAUUID', 
        columns='STAT_TYPE', 
        values='STAT_VALUE', 
        aggfunc='sum'
    ).fillna(0).reset_index()

    # --- KRITISK FIX: Tving match-nøglen til ren tekst ---
    pivot_stats['PLAYER_OPTAUUID'] = pivot_stats['PLAYER_OPTAUUID'].astype(str).str.strip()
    
    # Map navne
    pivot_stats['NAVN'] = pivot_stats['PLAYER_OPTAUUID'].map(name_map)
    
    # Backup: Hvis navnet mangler (f.eks. modstandere), vis ID
    pivot_stats['NAVN'] = pivot_stats['NAVN'].fillna(pivot_stats['PLAYER_OPTAUUID'].apply(lambda x: f"Ukendt ({x[:5]})"))

    # Beregn xG pr. 90
    if 'minsPlayed' in pivot_stats.columns and 'expectedGoals' in pivot_stats.columns:
        pivot_stats['xG_90'] = (pivot_stats['expectedGoals'] / pivot_stats['minsPlayed'].clip(lower=1) * 90)
    else:
        pivot_stats['xG_90'] = 0

    # --- 4. VISNING I TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["TRUP OVERSIGT", "INDIVIDUEL ANALYSE", "LINEBREAKS"])

    with tab_squad:
        st.subheader("Leaderboard")
        display_cols = ['NAVN', 'minsPlayed', 'expectedGoals', 'expectedAssists', 'xG_90']
        final_cols = [c for c in display_cols if c in pivot_stats.columns]
        
        st.dataframe(
            pivot_stats[final_cols].sort_values('expectedGoals', ascending=False),
            column_config={
                "NAVN": "Spiller",
                "minsPlayed": "Minutter",
                "expectedGoals": "Total xG",
                "expectedAssists": "Total xA",
                "xG_90": "xG/90"
            },
            use_container_width=True,
            hide_index=True
        )

    with tab_single:
        # Brug den færdige pivot-tabel til at styre dropdown
        # Sorteret alfabetisk efter NAVN
        sorted_pivot = pivot_stats.sort_values('NAVN')
        
        selected_name = st.selectbox(
            "Vælg Spiller", 
            options=sorted_pivot['NAVN'].tolist()
        )
        
        # Hent UUID baseret på det valgte navn
        selected_uuid = sorted_pivot[sorted_pivot['NAVN'] == selected_name]['PLAYER_OPTAUUID'].values[0]

        # Metrics
        p_xg = df_working[df_working['PLAYER_OPTAUUID'].astype(str).str.strip() == selected_uuid]
        
        m1, m2, m3, m4 = st.columns(4)
        def get_v(stat): return p_xg[p_xg['STAT_TYPE'] == stat]['STAT_VALUE'].sum()

        m1.metric("Total xG", f"{get_v('expectedGoals'):.2f}")
        m2.metric("Non-Penalty xG", f"{get_v('expectedGoalsNonpenalty'):.2f}")
        m3.metric("Total xA", f"{get_v('expectedAssists'):.2f}")
        m4.metric("Minutter", int(get_v('minsPlayed')))

        # Plot
        xg_cats = ['expectedGoalsHd', 'expectedGoalsOpenplay', 'expectedGoalsSetplay']
        xg_plot = p_xg[p_xg['STAT_TYPE'].isin(xg_cats)].groupby('STAT_TYPE')['STAT_VALUE'].sum().reset_index()
        if not xg_plot.empty and xg_plot['STAT_VALUE'].sum() > 0:
            st.plotly_chart(px.bar(xg_plot, x='STAT_TYPE', y='STAT_VALUE', color_discrete_sequence=['#df003b']), use_container_width=True)

    with tab_lb:
        if df_lb is not None and not df_lb.empty:
            # Match UUID i linebreak data
            df_lb['PLAYER_OPTAUUID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.strip()
            p_lb = df_lb[df_lb['PLAYER_OPTAUUID'] == selected_uuid].copy()
            if not p_lb.empty:
                lb_types = ['defenceLineBroken', 'midfieldLineBroken', 'attackingLineBroken']
                lb_data = p_lb[p_lb['STAT_TYPE'].isin(lb_types)]
                st.plotly_chart(px.bar(lb_data, y='STAT_TYPE', x=['STAT_FH', 'STAT_SH'], orientation='h', color_discrete_map={'STAT_FH': '#b8860b', 'STAT_SH': '#df003b'}), use_container_width=True)
