import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING ---
    df_xg = dp.get("xg_agg", pd.DataFrame())
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    df_shots = dp.get("playerstats", pd.DataFrame())
    name_map = dp.get("name_map", {})

    # DEBUG - god at have mens vi fikser
    st.write(f"DEBUG - Rækker i xG: {len(df_xg)}")

    if df_xg.empty:
        st.warning("⚠️ Ingen xG-data fundet. Prøv at vælge en anden kamp eller tjek din Snowflake forbindelse.")
        return

    # --- 2. DATA CLEANING ---
    df_xg.columns = [c.upper() for c in df_xg.columns]
    df_working = df_xg.copy()
    
    player_col = 'PLAYER_OPTAUUID'
    # Sikrer ensartet format på UUIDs
    df_working[player_col] = df_working[player_col].astype(str).str.strip().str.lower()

    # --- 3. PIVOTERING (Håndterer xG og xA) ---
    # Vi samler data pr. spiller, så vi har én række pr. mand
    pivot_stats = df_working.pivot_table(
        index=player_col, 
        columns='STAT_TYPE', 
        values='STAT_VALUE',
        aggfunc='sum'
    ).fillna(0).reset_index()

    # SIKRING: Opret kolonner hvis de mangler i data
    for col in ['expectedGoals', 'expectedAssists']:
        if col not in pivot_stats.columns:
            pivot_stats[col] = 0.0

    # TILFØJ NAVNE: Her fikser vi 'NAVN' fejlen
    # Vi mapper UUID til de læsbare navne vi har i systemet
    pivot_stats['NAVN'] = pivot_stats[player_col].map(name_map).fillna(pivot_stats[player_col])

    # --- 4. TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["OVERSIGT", "INDIVIDUEL PERFORMANCE", "LINEBREAKS"])

    with tab_squad:
        st.subheader("Holdoversigt - Forventede mål og assists")
        # Sorter efter xG (nu hvor vi ved den findes)
        display_df = pivot_stats[['NAVN', 'expectedGoals', 'expectedAssists']].sort_values('expectedGoals', ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    with tab_single:
        # Brug unikke navne til selectbox
        all_names = sorted(pivot_stats['NAVN'].unique())
        selected_name = st.selectbox("Vælg spiller", options=all_names, key="sb_performance")
        
        # Find UUID for den valgte spiller
        selected_uuid = pivot_stats[pivot_stats['NAVN'] == selected_name][player_col].values[0]
        p_row = pivot_stats[pivot_stats[player_col] == selected_uuid]
        
        # Metrics
        xg_val = p_row['expectedGoals'].values[0]
        xa_val = p_row['expectedAssists'].values[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total xG", f"{xg_val:.2f}")
        m2.metric("Total xA", f"{xa_val:.2f}")
        
        if not df_shots.empty:
            df_shots.columns = [c.upper() for c in df_shots.columns]
            p_shots = df_shots[df_shots[player_col].astype(str).str.lower() == selected_uuid]
            
            # Geometrisk DZ logik (hvis koordinater findes)
            if 'EVENT_X' in p_shots.columns:
                is_dz = (p_shots['EVENT_X'] >= 88.5) & (p_shots['EVENT_Y'].between(37, 63))
                m3.metric("Skud i DZ", int(is_dz.sum()))
            else:
                m3.metric("Skud i DZ", "N/A")
            m4.metric("Skud i alt", len(p_shots))

        # Plot
        fig = px.scatter(pivot_stats, x='expectedAssists', y='expectedGoals', text='NAVN', 
                         color='expectedGoals', color_continuous_scale='Reds',
                         labels={'expectedAssists': 'Forventede Assists (xA)', 'expectedGoals': 'Forventede Mål (xG)'},
                         title=f"xG vs xA Fordeling - {saeson_f}")
        fig.update_traces(textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

    with tab_lb:
        if not df_lb.empty:
            df_lb.columns = [c.upper() for c in df_lb.columns]
            p_lb_data = df_lb[df_lb[player_col].astype(str).str.lower() == selected_uuid]
            
            if not p_lb_data.empty:
                st.write(f"Linebreak analyse for **{selected_name}**")
                st.dataframe(p_lb_data, use_container_width=True, hide_index=True)
            else:
                st.info(f"Ingen registrerede linebreaks for {selected_name} i denne periode.")
        else:
            st.info("Ingen linebreak-data tilgængelig i databasen.")
