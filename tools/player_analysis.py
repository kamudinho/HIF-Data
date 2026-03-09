import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING ---
    df_xg = dp.get("xg_agg", pd.DataFrame())
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    df_shots = dp.get("playerstats", pd.DataFrame())
    name_map = dp.get("name_map", {})

    if df_xg.empty:
        st.warning("⚠️ Ingen data fundet i xG-tabellen.")
        return

    # --- 2. DATA CLEANING ---
    df_xg.columns = [c.upper() for c in df_xg.columns]
    df_working = df_xg.copy()
    
    player_col = 'PLAYER_OPTAUUID'
    stat_type_col = 'STAT_TYPE'
    stat_val_col = 'STAT_VALUE'

    # --- 3. PIVOTERING & ENSRETNING ---
    # Vi samler alle stats pr. spiller
    pivot_stats = df_working.pivot_table(
        index=player_col, 
        columns=stat_type_col, 
        values=stat_val_col,
        aggfunc='sum'
    ).fillna(0).reset_index()

    # Logik til at fange Optas specifikke navne fra dit dump
    # Vi mapper 'expectedGoalsNonpenalty' -> 'expectedGoals' hvis den mangler
    if 'expectedGoals' not in pivot_stats.columns and 'expectedGoalsNonpenalty' in pivot_stats.columns:
        pivot_stats['expectedGoals'] = pivot_stats['expectedGoalsNonpenalty']
    
    if 'expectedAssists' not in pivot_stats.columns and 'expectedAssistsOpenplay' in pivot_stats.columns:
        pivot_stats['expectedAssists'] = pivot_stats['expectedAssistsOpenplay']

    # Sikr at kolonnerne findes (minsPlayed og touches er i dit dump)
    cols_to_ensure = ['expectedGoals', 'expectedAssists', 'minsPlayed', 'touches']
    for col in cols_to_ensure:
        if col not in pivot_stats.columns:
            pivot_stats[col] = 0.0

    # Tilføj læsbart navn
    pivot_stats['NAVN'] = pivot_stats[player_col].map(name_map).fillna(pivot_stats[player_col])

    # --- 4. VISNING (TABS) ---
    tab_squad, tab_single, tab_lb = st.tabs(["🏆 OVERSIGT", "👤 INDIVIDUEL", "📈 LINEBREAKS"])

    with tab_squad:
        st.subheader("Holdoversigt - Sæson Performance")
        # Tabel med de vigtigste metrics
        display_df = pivot_stats[['NAVN', 'minsPlayed', 'expectedGoals', 'expectedAssists', 'touches']].sort_values('expectedGoals', ascending=False)
        
        st.dataframe(
            display_df.style.format({
                'expectedGoals': '{:.2f}', 
                'expectedAssists': '{:.2f}', 
                'minsPlayed': '{:.0f}',
                'touches': '{:.0f}'
            }), 
            use_container_width=True, hide_index=True
        )

    with tab_single:
        all_names = sorted(pivot_stats['NAVN'].unique())
        selected_name = st.selectbox("Vælg spiller", options=all_names, key="sb_perf_new")
        
        # Udtræk række for valgt spiller
        p_row = pivot_stats[pivot_stats['NAVN'] == selected_name].iloc[0]
        p_uuid = p_row[player_col]

        # Metrics række
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Minutter", int(p_row['minsPlayed']))
        m2.metric("Total xG", f"{p_row['expectedGoals']:.2f}")
        m3.metric("Total xA", f"{p_row['expectedAssists']:.2f}")
        m4.metric("Touches", int(p_row['touches']))

        # Graf: xG vs xA for alle spillere
        fig = px.scatter(pivot_stats, x='expectedAssists', y='expectedGoals', 
                         hover_name='NAVN', size='minsPlayed',
                         color='expectedGoals', color_continuous_scale='Reds',
                         labels={'expectedAssists': 'xA (Forventede Assists)', 'expectedGoals': 'xG (Forventede Mål)'},
                         title=f"xG vs xA Fordeling")
        st.plotly_chart(fig, use_container_width=True)

    with tab_lb:
        if not df_lb.empty:
            df_lb.columns = [c.upper() for c in df_lb.columns]
            # Vi matcher på UUID for at undgå navne-fejl
            p_lb_data = df_lb[df_lb[player_col] == p_uuid]
            
            if not p_lb_data.empty:
                st.write(f"Linebreak analyse for **{selected_name}**")
                # Gruppér per type (F.eks. 'Linebreak Complete')
                lb_summary = p_lb_data.groupby('STAT_TYPE')['STAT_TOTAL'].sum().reset_index()
                st.bar_chart(lb_summary.set_index('STAT_TYPE'))
                st.dataframe(p_lb_data[['STAT_TYPE', 'STAT_TOTAL']], use_container_width=True, hide_index=True)
            else:
                st.info(f"Ingen linebreaks fundet for {selected_name}.")
        else:
            st.info("Linebreak-data ikke tilgængelig.")
