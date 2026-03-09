import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING ---
    df_xg = dp.get("xg_agg", pd.DataFrame())
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    name_map = dp.get("name_map", {})

    if df_xg.empty:
        st.warning("Ingen data fundet i xG-tabellen.")
        return

    # --- 2. FORBEREDELSE AF SPILLER-LISTE (Fra xG data) ---
    # Vi bruger xG tabellen til at lave vores hovedliste af spillere
    df_xg.columns = [c.upper() for c in df_xg.columns]
    
    # Pivot xG data for at få en pæn oversigt
    pivot_stats = df_xg.pivot_table(
        index='PLAYER_OPTAUUID', 
        columns='STAT_TYPE', 
        values='STAT_VALUE',
        aggfunc='sum'
    ).fillna(0).reset_index()

    # Navne-mapping
    pivot_stats['NAVN'] = pivot_stats['PLAYER_OPTAUUID'].map(name_map).fillna(pivot_stats['PLAYER_OPTAUUID'])
    
    # --- 3. VISNING ---
    st.title("Hvidovre IF - Spillere")
    
    tab_squad, tab_single = st.tabs(["Trupoversigt", "Individuel Performance"])

    with tab_squad:
        st.subheader("Truppen - Sæson Performance")
        st.dataframe(pivot_stats[['NAVN', 'expectedGoals', 'expectedAssists']].sort_values('expectedGoals', ascending=False), 
                     use_container_width=True, hide_index=True)

    with tab_single:
        all_names = sorted(pivot_stats['NAVN'].unique())
        selected_name = st.selectbox("Vælg spiller", options=all_names)
        
        # Find spillerens UUID
        p_uuid = pivot_stats[pivot_stats['NAVN'] == selected_name]['PLAYER_OPTAUUID'].values[0]

        # --- LINEBREAK SEKTION (Baseret på dit dump) ---
        st.write(f"Linebreak Analyse: {selected_name}")
        
        if not df_lb.empty:
            # Tving kolonner til store bogstaver for at matche dit dump
            df_lb.columns = [c.upper() for c in df_lb.columns]
            
            # Filtrer på spillerens UUID
            # OBS: I dit dump ser det ud til at kolonnen hedder PLAYER_OPTAUUID
            p_lb_data = df_lb[df_lb['PLAYER_OPTAUUID'] == p_uuid].copy()
            
            if not p_lb_data.empty:
                # Vi fjerner 'percentage' rækkerne for at få en ren bar-chart af tællinger
                plot_data = p_lb_data[~p_lb_data['STAT_TYPE'].str.contains('percentage', na=False)]
                
                # Lav bar chart
                fig_lb = px.bar(plot_data, 
                                x='STAT_TYPE', 
                                y='STAT_VALUE',
                                labels={'STAT_VALUE': 'Antal', 'STAT_TYPE': 'Type'},
                                color='STAT_VALUE',
                                color_continuous_scale='Reds')
                st.plotly_chart(fig_lb, use_container_width=True)
                
                # Vis rækkerne som de ser ud i dit dump
                st.dataframe(p_lb_data[['STAT_TYPE', 'STAT_VALUE']], use_container_width=True, hide_index=True)
            else:
                st.info(f"Ingen linebreak-rækker fundet for UUID: {p_uuid}")
        else:
            st.error("df_lb er tom - tjek om data bliver indlæst korrekt fra Snowflake.")
