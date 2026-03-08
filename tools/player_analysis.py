import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    """
    HIF Spillerperformance Analyse
    Fokuserer på xG, xA og geografiske Danger Zone (DZ) beregninger.
    """
    
    # --- 1. DATA HENTNING ---
    df_xg = dp.get("xg_agg")        # Fra OPTA_MATCHEXPECTEDGOALS
    df_lb = dp.get("linebreaks")    # Fra OPTA_PLAYERLINEBREAKINGPASSAGGREGATES
    df_shots = dp.get("playerstats") # Fra OPTA_EVENTS (indeholder koordinater)
    name_map = dp.get("name_map", {})

    if df_xg is None or df_xg.empty:
        st.warning("⚠️ Ingen xG-data fundet. Tjek liga/sæson-valg.")
        return

    # --- 2. ENSRETNING AF KOLONNER & UUIDs ---
    df_xg.columns = [c.upper() for c in df_xg.columns]
    df_working = df_xg.copy()
    df_working['PLAYER_OPTAUUID'] = df_working['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
    df_working['STAT_VALUE'] = pd.to_numeric(df_working['STAT_VALUE'], errors='coerce').fillna(0)

    if df_shots is not None and not df_shots.empty:
        df_shots.columns = [c.upper() for c in df_shots.columns]
        df_shots['PLAYER_OPTAUUID'] = df_shots['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
        
        # --- DZ LOGIK (GEOMETRISK - SAMME SOM I DIT SHOTMAP) ---
        # Vi bruger koordinaterne fra OPTA_EVENTS til at definere DZ
        df_shots['IS_DZ_GEO'] = (df_shots['EVENT_X'] >= 88.5) & \
                                (df_shots['EVENT_Y'] >= 37.0) & \
                                (df_shots['EVENT_Y'] <= 63.0)

    if df_lb is not None and not df_lb.empty:
        df_lb.columns = [c.upper() for c in df_lb.columns]
        df_lb['PLAYER_OPTAUUID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()

    # --- 3. PIVOTERING AF STATS ---
    pivot_stats = df_working.pivot_table(
        index='PLAYER_OPTAUUID', 
        columns='STAT_TYPE', 
        values='STAT_VALUE', 
        aggfunc='sum'
    ).fillna(0).reset_index()
    
    pivot_stats['NAVN'] = pivot_stats['PLAYER_OPTAUUID'].map(name_map)
    pivot_stats['NAVN'] = pivot_stats['NAVN'].fillna(pivot_stats['PLAYER_OPTAUUID'].apply(lambda x: f"Ukendt ({x[:5]})"))

    # --- 4. RENDER TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["📊 OVERSIGT", "👤 INDIVIDUEL PERFORMANCE", "📈 LINEBREAKS"])

    with tab_squad:
        st.subheader("Holdets xG Performance")
        cols_to_show = ['NAVN', 'expectedGoals', 'expectedAssists', 'minsPlayed']
        existing_cols = [c for c in cols_to_show if c in pivot_stats.columns]
        
        st.dataframe(
            pivot_stats[existing_cols].sort_values('expectedGoals', ascending=False), 
            use_container_width=True, 
            hide_index=True
        )
        
    with tab_single:
        sorted_names = sorted(pivot_stats['NAVN'].unique())
        selected_name = st.selectbox("Vælg spiller", options=sorted_names)
        
        selected_uuid = pivot_stats[pivot_stats['NAVN'] == selected_name]['PLAYER_OPTAUUID'].values[0]
        p_xg_data = pivot_stats[pivot_stats['PLAYER_OPTAUUID'] == selected_uuid]

        # Beregn DZ stats baseret på koordinaterne i df_shots
        dz_total = 0
        total_shots = 0
        if df_shots is not None and not df_shots.empty:
            p_shots = df_shots[df_shots['PLAYER_OPTAUUID'] == selected_uuid]
            total_shots = len(p_shots)
            dz_total = p_shots['IS_DZ_GEO'].sum()

        # Metrics række
        m1, m2, m3, m4 = st.columns(4)
        xg_val = p_xg_data['expectedGoals'].values[0] if 'expectedGoals' in p_xg_data.columns else 0
        xa_val = p_xg_data['expectedAssists'].values[0] if 'expectedAssists' in p_xg_data.columns else 0

        m1.metric("Total xG", f"{xg_val:.2f}")
        m2.metric("Total xA", f"{xa_val:.2f}")
        m3.metric("Skud i DZ", int(dz_total), help="Geometrisk Danger Zone: X >= 88.5, Y mellem 37 og 63")
        m4.metric("Skud i alt", total_shots)

        st.markdown("---")
        
        # Visualisering: xG vs xA scatter plot for hele truppen
        fig_scatter = px.scatter(
            pivot_stats, x='expectedAssists', y='expectedGoals', 
            text='NAVN', title="xG vs xA Fordeling",
            color='expectedGoals', color_continuous_scale='Reds',
            labels={'expectedAssists': 'Forventede Assists (xA)', 'expectedGoals': 'Forventede Mål (xG)'}
        )
        fig_scatter.update_traces(textposition='top center')
        st.plotly_chart(fig_scatter, use_container_width=True)

    with tab_lb:
        if df_lb is not None and not df_lb.empty:
            p_lb = df_lb[df_lb['PLAYER_OPTAUUID'] == selected_uuid].copy()
            
            if not p_lb.empty:
                # Sørg for numeriske værdier
                for col in ['STAT_VALUE', 'STAT_FH', 'STAT_SH']:
                    if col in p_lb.columns:
                        p_lb[col] = pd.to_numeric(p_lb[col], errors='coerce').fillna(0)

                def get_lb_sum(stat_name):
                    return p_lb[p_lb['STAT_TYPE'] == stat_name]['STAT_VALUE'].sum()

                l1, l2, l3, l4 = st.columns(4)
                l1.metric("Linebreaks I alt", int(get_lb_sum('total')))
                l2.metric("Under Pres", int(get_lb_sum('underPressure')))
                l3.metric("Farlige", int(get_lb_sum('leadingToDanger')))
                l4.metric("Til Skud", int(get_lb_sum('leadingToShots')))

                st.markdown("---")
                
                # Bar chart over hvilke kæder der brydes
                lb_viz_data = pd.DataFrame({
                    'Kæde': ['Modst. Forsvar', 'Modst. Midtbane', 'Modst. Angreb'],
                    'Antal': [
                        get_lb_sum('defenceLineBroken'),
                        get_lb_sum('midfieldLineBroken'),
                        get_lb_sum('attackingLineBroken')
                    ]
                })
                fig_lb = px.bar(lb_viz_data, x='Antal', y='Kæde', orientation='h', 
                               title=f"Hvilke linjer bryder {selected_name}?",
                               color='Antal', color_continuous_scale='Reds')
                st.plotly_chart(fig_lb, use_container_width=True)
            else:
                st.info(f"Ingen linebreak-data fundet for {selected_name}.")
        else:
            st.error("Linebreak-data er ikke tilgængeligt.")
