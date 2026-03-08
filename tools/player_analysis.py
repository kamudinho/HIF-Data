import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    """
    HIF Spillerperformance Analyse
    Mapper data fra Analyse_load (get_analysis_package) til visuelle metrics og grafer.
    """
    
    # --- 1. DATA MAPPING (Kobling til dine SQL resultater) ---
    # Vi bruger de præcise nøgler fra din get_analysis_package()
    df_xg = dp.get("xg_agg")        
    df_lb = dp.get("linebreaks")    
    df_shots = dp.get("playerstats")
    df_quals = dp.get("qualifiers") 
    name_map = dp.get("name_map", {})

    # Tjek om xG-data er landet korrekt
    if df_xg is None or df_xg.empty:
        st.warning("⚠️ Ingen xG-data fundet i 'xg_agg'. Tjek liga/sæson-valg eller hif_only filteret.")
        return

    # --- 2. DATA RENSNING & ENSRETNING ---
    # Tving kolonnenavne til UPPERCASE for at matche SQL output fra Snowflake
    df_xg.columns = [c.upper() for c in df_xg.columns]
    df_working = df_xg.copy()
    
    # Konvertér værdier til tal og UUIDs til små bogstaver for fejlfrit map
    df_working['STAT_VALUE'] = pd.to_numeric(df_working['STAT_VALUE'], errors='coerce').fillna(0)
    df_working['PLAYER_OPTAUUID'] = df_working['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
    
    if df_shots is not None and not df_shots.empty:
        df_shots.columns = [c.upper() for c in df_shots.columns]
        df_shots['PLAYER_OPTAUUID'] = df_shots['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()

    if df_quals is not None and not df_quals.empty:
        df_quals.columns = [c.upper() for c in df_quals.columns]

    if df_lb is not None and not df_lb.empty:
        df_lb.columns = [c.upper() for c in df_lb.columns]
        df_lb['PLAYER_OPTAUUID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()

    # --- 3. PIVOTERING AF STATS ---
    # Laver STAT_TYPE (expectedGoals, minsPlayed osv.) om til egne kolonner
    pivot_stats = df_working.pivot_table(
        index='PLAYER_OPTAUUID', 
        columns='STAT_TYPE', 
        values='STAT_VALUE', 
        aggfunc='sum'
    ).fillna(0).reset_index()
    
    # Tilføj spillernavne fra players.csv mappet
    pivot_stats['NAVN'] = pivot_stats['PLAYER_OPTAUUID'].map(name_map)
    pivot_stats['NAVN'] = pivot_stats['NAVN'].fillna(pivot_stats['PLAYER_OPTAUUID'].apply(lambda x: f"Ukendt ({x[:5]})"))

    # --- 4. DANGER ZONE LOGIK (Q16 & Q17) ---
    if df_shots is not None and not df_shots.empty and df_quals is not None:
        # Finder alle Event UUIDs der har Qualifiers for 'The Danger Zone'
        dz_events = df_quals[df_quals['QUALIFIER_QID'].astype(str).isin(['16', '17'])]['EVENT_OPTAUUID'].unique()
        df_shots['IS_DZ'] = df_shots['EVENT_OPTAUUID'].isin(dz_events)

    # --- 5. RENDER TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["📊 OVERSIGT", "👤 INDIVIDUEL", "📈 LINEBREAKS"])

    with tab_squad:
        st.subheader("Holdets xG Performance")
        # Dynamisk kolonne-tjek (viser kun det der findes i data)
        cols_to_show = ['NAVN', 'expectedGoals', 'expectedAssists', 'expectedGoalsConceded', 'minsPlayed']
        existing_cols = [c for c in cols_to_show if c in pivot_stats.columns]
        
        st.dataframe(
            pivot_stats[existing_cols].sort_values('expectedGoals', ascending=False), 
            use_container_width=True, 
            hide_index=True
        )
        
    with tab_single:
        sorted_names = sorted(pivot_stats['NAVN'].unique())
        selected_name = st.selectbox("Vælg Spiller til detaljeret analyse", options=sorted_names)
        
        # Hent UUID for den valgte spiller
        selected_uuid = pivot_stats[pivot_stats['NAVN'] == selected_name]['PLAYER_OPTAUUID'].values[0]
        p_data = pivot_stats[pivot_stats['PLAYER_OPTAUUID'] == selected_uuid]

        # Danger Zone Stats (Skud tæller)
        dz_total = 0
        if df_shots is not None and 'IS_DZ' in df_shots.columns:
            dz_total = len(df_shots[(df_shots['PLAYER_OPTAUUID'] == selected_uuid) & (df_shots['IS_DZ'] == True)])

        # Top Metrics
        m1, m2, m3, m4 = st.columns(4)
        xg_val = p_data['expectedGoals'].values[0] if 'expectedGoals' in p_data.columns else 0
        xa_val = p_data['expectedAssists'].values[0] if 'expectedAssists' in p_data.columns else 0
        total_shots = len(df_shots[df_shots['PLAYER_OPTAUUID'] == selected_uuid]) if df_shots is not None else 0

        m1.metric("Total xG", f"{xg_val:.2f}")
        m2.metric("Total xA", f"{xa_val:.2f}")
        m3.metric("Danger Zone Skud", dz_total, help="Skud fra det centrale felt i feltet (Q16/Q17)")
        m4.metric("Skud i alt", total_shots)

        st.markdown("---")
        
        # Grafik: xG vs xA Fordeling (Hvis data findes)
        if not pivot_stats.empty:
            fig_scatter = px.scatter(
                pivot_stats, x='expectedAssists', y='expectedGoals', 
                text='NAVN', title="xG vs xA (Hele Truppen)",
                color='expectedGoals', color_continuous_scale='Reds'
            )
            fig_scatter.update_traces(textposition='top center')
            st.plotly_chart(fig_scatter, use_container_width=True)

    with tab_lb:
        if df_lb is not None and not df_lb.empty:
            # Filtrér på den valgte spiller fra tab_single
            p_lb = df_lb[df_lb['PLAYER_OPTAUUID'] == selected_uuid].copy()
            
            if not p_lb.empty:
                # Helper til at summere specifikke linebreak stats
                def get_lb_sum(stat_name):
                    return p_lb[p_lb['STAT_TYPE'] == stat_name]['STAT_VALUE'].sum()

                l1, l2, l3, l4 = st.columns(4)
                l1.metric("Linebreaks", int(get_lb_sum('total')))
                l2.metric("Under Pres", int(get_lb_sum('underPressure')))
                l3.metric("Farlige", int(get_lb_sum('leadingToDanger')))
                l4.metric("Gennem 3 kæder", int(get_lb_sum('threeLines')))

                st.markdown("---")
                
                # Visualisering af kæder der brydes
                lb_data = pd.DataFrame({
                    'Type': ['Modstander Angreb', 'Modstander Midtbane', 'Modstander Forsvar'],
                    'Antal': [
                        get_lb_sum('attackingLineBroken'), 
                        get_lb_sum('midfieldLineBroken'), 
                        get_lb_sum('defenceLineBroken')
                    ]
                })
                fig_lb = px.bar(lb_data, x='Antal', y='Type', orientation='h', 
                               title=f"Hvilke kæder bryder {selected_name}?",
                               color='Antal', color_continuous_scale='Greys')
                st.plotly_chart(fig_lb, use_container_width=True)
            else:
                st.info(f"Ingen linebreak-data registreret for {selected_name}.")
        else:
            st.error("Linebreak-data er ikke tilgængeligt i den nuværende datapakke.")

# Færdig
