import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING ---
    df_xg = dp.get("xg_agg", pd.DataFrame())
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    df_shots = dp.get("playerstats", pd.DataFrame())
    name_map = dp.get("name_map", {})

    # Konstanter fra din konfiguration
    HIF_WYID = 7490 

    if df_xg.empty:
        st.warning("⚠️ Ingen data fundet for Hvidovre IF i xG-tabellen.")
        return

    # --- 2. DATA CLEANING & FILTRERING ---
    df_xg.columns = [c.upper() for c in df_xg.columns]
    
    # Vi sikrer, at vi kun ser på Hvidovre IF (hvis hold-id findes i din query)
    # Hvis din query allerede er filtreret til HIF, kan denne linje udelades
    if 'TEAM_WYID' in df_xg.columns:
        df_working = df_xg[df_xg['TEAM_WYID'] == HIF_WYID].copy()
    else:
        df_working = df_xg.copy()
    
    player_col = 'PLAYER_OPTAUUID'
    stat_type_col = 'STAT_TYPE'
    stat_val_col = 'STAT_VALUE'

    # --- 3. PIVOTERING ---
    pivot_stats = df_working.pivot_table(
        index=player_col, 
        columns=stat_type_col, 
        values=stat_val_col,
        aggfunc='sum'
    ).fillna(0).reset_index()

    # Ensretning af Opta-navne (xG / xA)
    rename_rules = {
        'expectedGoalsNonpenalty': 'expectedGoals',
        'expectedAssistsOpenplay': 'expectedAssists'
    }
    for old, new in rename_rules.items():
        if old in pivot_stats.columns and new not in pivot_stats.columns:
            pivot_stats[new] = pivot_stats[old]

    # Sikr standard kolonner
    for col in ['expectedGoals', 'expectedAssists', 'minsPlayed', 'touches']:
        if col not in pivot_stats.columns:
            pivot_stats[col] = 0.0

    # Navne-mapping
    pivot_stats['NAVN'] = pivot_stats[player_col].map(name_map).fillna(pivot_stats[player_col])

    # --- 4. VISNING ---
    st.title("🔴 Hvidovre IF - Spillere")
    
    t1, t2, t3 = st.tabs(["📋 Trupoversigt", "📊 xG vs xA", "⛓️ Linebreaks"])

    with t1:
        st.subheader("HIF Truppen - Sæsonstats")
        # Fokus på minutter og de forventede mål/assists
        display_df = pivot_stats[['NAVN', 'minsPlayed', 'expectedGoals', 'expectedAssists', 'touches']].sort_values('minsPlayed', ascending=False)
        
        st.dataframe(
            display_df.style.format({
                'expectedGoals': '{:.2f}', 
                'expectedAssists': '{:.2f}', 
                'minsPlayed': '{:.0f}',
                'touches': '{:.0f}'
            }), 
            use_container_width=True, hide_index=True
        )

    with t2:
        # Scatter plot kun for HIF spillere
        fig = px.scatter(pivot_stats, x='expectedAssists', y='expectedGoals', 
                         hover_name='NAVN', size='minsPlayed',
                         text='NAVN',
                         color_continuous_scale='Reds',
                         labels={'expectedAssists': 'xA', 'expectedGoals': 'xG'},
                         title="HIF Internt: xG vs xA")
        fig.update_traces(textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

    with t3:
        all_names = sorted(pivot_stats['NAVN'].unique())
        sel_name = st.selectbox("Vælg HIF spiller for Linebreak-detaljer", all_names)
        
        p_uuid = pivot_stats[pivot_stats['NAVN'] == sel_name][player_col].values[0]

        if not df_lb.empty:
            df_lb.columns = [c.upper() for c in df_lb.columns]
            p_lb = df_lb[df_lb[player_col] == p_uuid]
            
            if not p_lb.empty:
                st.bar_chart(p_lb.groupby('STAT_TYPE')['STAT_TOTAL'].sum())
                st.dataframe(p_lb[['STAT_TYPE', 'STAT_TOTAL']], use_container_width=True, hide_index=True)
            else:
                st.info(f"Ingen linebreak-data fundet for {sel_name}.")
