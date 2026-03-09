import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING (Rettet til at matche dine SQL keys) ---
    df_xg = dp.get("xg_agg", pd.DataFrame())
    
    # For linebreaks bruger vi også de flade keys fra din pakke
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    df_shots = dp.get("playerstats", pd.DataFrame())
    name_map = dp.get("name_map", {})

    # DEBUG
    st.write(f"DEBUG - Rækker i xG: {len(df_xg)}")

    if df_xg.empty:
        st.warning("⚠️ Ingen xG-data fundet i 'xg_agg'.")
        return

    # --- 2. DATA CLEANING & DZ LOGIK ---
    df_xg.columns = [c.upper() for c in df_xg.columns]
    df_working = df_xg.copy()
    
    # Vi sikrer os at vi har de rigtige kolonnenavne efter UPPERCASE
    player_col = 'PLAYER_OPTAUUID'
    stat_type_col = 'STAT_TYPE'
    stat_val_col = 'STAT_VALUE'

    df_working[player_col] = df_working[player_col].astype(str).str.strip().str.lower()

    if not df_shots.empty:
        df_shots.columns = [c.upper() for c in df_shots.columns]
        df_shots['PLAYER_OPTAUUID'] = df_shots['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
        # Din geometriske Danger Zone definition
        df_shots['IS_DZ_GEO'] = (df_shots['EVENT_X'] >= 88.5) & \
                                (df_shots['EVENT_Y'] >= 37.0) & \
                                (df_shots['EVENT_Y'] <= 63.0)

    # --- 3. PIVOTERING ---
    # Vi bruger de kolonnenavne din SQL returnerer: STAT_TYPE og STAT_VALUE
    pivot_stats = df_working.pivot_table(
        index=player_col, 
        columns=stat_type_col, 
        values=stat_val_col, 
        aggfunc='sum'
    ).fillna(0).reset_index()
    
    # Mapping af navne
    pivot_stats['NAVN'] = pivot_stats[player_col].map(name_map)
    pivot_stats['NAVN'] = pivot_stats['NAVN'].fillna(pivot_stats[player_col])

    # --- 4. TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["OVERSIGT", "INDIVIDUEL PERFORMANCE", "LINEBREAKS"])

    with tab_squad:
        # Sorter efter xG hvis kolonnen findes
        sort_col = 'expectedGoals' if 'expectedGoals' in pivot_stats.columns else pivot_stats.columns[1]
        st.dataframe(pivot_stats.sort_values(sort_col, ascending=False), use_container_width=True, hide_index=True)

    with tab_single:
        selected_name = st.selectbox("Vælg spiller", options=sorted(pivot_stats['NAVN'].unique()), key="sb_performance")
        selected_uuid = pivot_stats[pivot_stats['NAVN'] == selected_name][player_col].values[0]
        
        p_row = pivot_stats[pivot_stats[player_col] == selected_uuid]
        
        # Metrics række med fallback til 0
        xg_val = p_row['expectedGoals'].values[0] if 'expectedGoals' in p_row.columns else 0.0
        xa_val = p_row['expectedAssists'].values[0] if 'expectedAssists' in p_row.columns else 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total xG", f"{xg_val:.2f}")
        m2.metric("Total xA", f"{xa_val:.2f}")
        
        if not df_shots.empty:
            p_shots = df_shots[df_shots['PLAYER_OPTAUUID'] == selected_uuid]
            m3.metric("Skud i DZ", int(p_shots['IS_DZ_GEO'].sum()))
            m4.metric("Skud i alt", len(p_shots))

        # Scatter plot
        if 'expectedAssists' in pivot_stats.columns and 'expectedGoals' in pivot_stats.columns:
            fig = px.scatter(pivot_stats, x='expectedAssists', y='expectedGoals', text='NAVN', 
                             color='expectedGoals', color_continuous_scale='Reds',
                             title="xG vs xA Fordeling")
            st.plotly_chart(fig, use_container_width=True)

    with tab_lb:
        if not df_lb.empty:
            df_lb.columns = [c.upper() for c in df_lb.columns]
            # Match UUID
            p_lb = df_lb[df_lb['PLAYER_OPTAUUID'].astype(str).str.lower() == selected_uuid]
            st.write(f"Linebreak analyse for {selected_name}")
            st.dataframe(p_lb, use_container_width=True)
        else:
            st.info("Ingen linebreak-data tilgængelig.")
