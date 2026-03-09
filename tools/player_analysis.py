#tools/player_analysis.py
import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING ---
    df_xg = dp.get("xg_agg", pd.DataFrame())
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    df_shots = dp.get("playerstats", pd.DataFrame())
    name_map = dp.get("name_map", {})

    st.write("DEBUG - Antal rækker i xG:", len(df_xg))
        if not df_xg.empty:
            st.write("DEBUG - Første 3 rækker:", df_xg.head(3))
            st.write("DEBUG - Tilgængelige STAT_TYPES:", df_xg['STAT_TYPE'].unique())

    
    if df_xg is None or df_xg.empty:
        st.warning("⚠️ Ingen xG-data fundet.")
        return

    # --- 2. DATA CLEANING & DZ LOGIK ---
    df_xg.columns = [c.upper() for c in df_xg.columns]
    df_working = df_xg.copy()
    df_working['PLAYER_OPTAUUID'] = df_working['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()

    if not df_shots.empty:
        df_shots.columns = [c.upper() for c in df_shots.columns]
        df_shots['PLAYER_OPTAUUID'] = df_shots['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
        # Din geometriske Danger Zone definition
        df_shots['IS_DZ_GEO'] = (df_shots['EVENT_X'] >= 88.5) & \
                                (df_shots['EVENT_Y'] >= 37.0) & \
                                (df_shots['EVENT_Y'] <= 63.0)

    # --- 3. PIVOTERING ---
    pivot_stats = df_working.pivot_table(
        index='PLAYER_OPTAUUID', 
        columns='STAT_TYPE', 
        values='STAT_VALUE', 
        aggfunc='sum'
    ).fillna(0).reset_index()
    
    pivot_stats['NAVN'] = pivot_stats['PLAYER_OPTAUUID'].map(name_map)
    pivot_stats['NAVN'] = pivot_stats['NAVN'].fillna(pivot_stats['PLAYER_OPTAUUID'])

    # --- 4. TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["OVERSIGT", "INDIVIDUEL PERFORMANCE", "LINEBREAKS"])

    with tab_squad:
        st.dataframe(pivot_stats.sort_values('expectedGoals', ascending=False), use_container_width=True, hide_index=True)

    with tab_single:
        selected_name = st.selectbox("Vælg spiller", options=sorted(pivot_stats['NAVN'].unique()))
        selected_uuid = pivot_stats[pivot_stats['NAVN'] == selected_name]['PLAYER_OPTAUUID'].values[0]
        
        # Metrics række
        m1, m2, m3, m4 = st.columns(4)
        p_row = pivot_stats[pivot_stats['PLAYER_OPTAUUID'] == selected_uuid]
        m1.metric("Total xG", f"{p_row['expectedGoals'].values[0]:.2f}")
        m2.metric("Total xA", f"{p_row['expectedAssists'].values[0]:.2f}")
        
        if not df_shots.empty:
            p_shots = df_shots[df_shots['PLAYER_OPTAUUID'] == selected_uuid]
            m3.metric("Skud i DZ", int(p_shots['IS_DZ_GEO'].sum()))
            m4.metric("Skud i alt", len(p_shots))

        st.plotly_chart(px.scatter(pivot_stats, x='expectedAssists', y='expectedGoals', text='NAVN', color='expectedGoals', color_continuous_scale='Reds'), use_container_width=True)

    with tab_lb:
        if df_lb is not None and not df_lb.empty:
            df_lb.columns = [c.upper() for c in df_lb.columns]
            p_lb = df_lb[df_lb['PLAYER_OPTAUUID'].astype(str).str.lower() == selected_uuid]
            # Din bar-chart logik for linjebrud her...
            st.write(f"Linebreak analyse for {selected_name}")
            st.dataframe(p_lb, use_container_width=True)
