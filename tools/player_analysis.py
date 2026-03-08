import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. HENT DATA (Navne rettet til at matche din get_opta_queries) ---
    df_xg = dp.get("opta_expected_goals")  # Rettet fra xg_agg
    df_lb = dp.get("opta_linebreaks")      # Rettet fra linebreaks
    df_shots = dp.get("opta_shotevents")   # Rettet fra playerstats
    df_quals = dp.get("opta_qualifiers")   # Rettet fra qualifiers
    
    # Hent name_map
    raw_name_map = dp.get("name_map", {})
    name_map = {str(k).strip().lower(): str(v).strip() for k, v in raw_name_map.items()}

    if df_xg is None or df_xg.empty:
        st.warning("Ingen xG-data fundet.")
        return

    # --- 2. FORBEREDELSE AF DATA ---
    df_working = df_xg.copy()
    df_working['STAT_VALUE'] = pd.to_numeric(df_working['STAT_VALUE'], errors='coerce').fillna(0)
    df_working['PLAYER_OPTAUUID'] = df_working['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
    
    if df_shots is not None:
        df_shots['PLAYER_OPTAUUID'] = df_shots['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()

    # --- 3. PIVOTERING ---
    pivot_stats = df_working.pivot_table(
        index='PLAYER_OPTAUUID', 
        columns='STAT_TYPE', 
        values='STAT_VALUE', 
        aggfunc='sum'
    ).fillna(0).reset_index()
    pivot_stats['NAVN'] = pivot_stats['PLAYER_OPTAUUID'].map(name_map)
    pivot_stats['NAVN'] = pivot_stats['NAVN'].fillna(pivot_stats['PLAYER_OPTAUUID'].apply(lambda x: f"Ukendt ({x[:5]})"))

    # --- 4. DANGER ZONE LOGIK ---
    if df_shots is not None and df_quals is not None:
        # Opta Danger Zone Qualifiers
        danger_ids = [16, 17, '16', '17']
        dz_events = df_quals[df_quals['QUALIFIER_QID'].isin(danger_ids)]['EVENT_OPTAUUID'].unique()
        df_shots['IS_DZ'] = df_shots['EVENT_OPTAUUID'].isin(dz_events)

    # --- TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["OVERSIGT", "INDIVIDUEL ANALYSE", "LINEBREAKS"])

    with tab_squad:
        display_cols = ['NAVN', 'expectedGoals', 'expectedAssists']
        st.dataframe(pivot_stats[[c for c in display_cols if c in pivot_stats.columns]].sort_values('expectedGoals', ascending=False), 
                     use_container_width=True, hide_index=True)
        
    with tab_single:
        sorted_pivot = pivot_stats.sort_values('NAVN')
        selected_name = st.selectbox("Vælg Spiller", options=sorted_pivot['NAVN'].tolist())
        selected_uuid = sorted_pivot[sorted_pivot['NAVN'] == selected_name]['PLAYER_OPTAUUID'].values[0]

        # DZ Tæller via UUID
        dz_total = 0
        if df_shots is not None:
            p_dz = df_shots[(df_shots['PLAYER_OPTAUUID'] == selected_uuid) & (df_shots['IS_DZ'] == True)]
            dz_total = len(p_dz)

        # Metrics
        p_xg = df_working[df_working['PLAYER_OPTAUUID'] == selected_uuid]
        def get_v(stat): return p_xg[p_xg['STAT_TYPE'] == stat]['STAT_VALUE'].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total xG", f"{get_v('expectedGoals'):.2f}")
        m2.metric("Total xA", f"{get_v('expectedAssists'):.2f}")
        m3.metric("Skud i DZ", dz_total) # NU SKAL DENNE VIRKE
        m4.metric("Skud i alt", len(df_shots[df_shots['PLAYER_OPTAUUID'] == selected_uuid]) if df_shots is not None else 0)

        st.markdown("---")
        # (Resten af dine grafer her...)

                col_left, col_right = st.columns(2)
                with col_left:
                    lb_zones = pd.DataFrame({
                        'Kæde': ['Forsvar', 'Midtbane', 'Angreb'],
                        'Antal': [get_lb('attackingLineBroken'), get_lb('midfieldLineBroken'), get_lb('defenceLineBroken')]
                    })
                    fig_zones = px.bar(lb_zones, x='Antal', y='Kæde', orientation='h', title="Hvilke kæder brydes?",
                                       color='Kæde', color_discrete_map={'Forsvar': '#df003b', 'Midtbane': '#b8860b', 'Angreb': '#333333'})
                    fig_zones.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_zones, use_container_width=True)

                with col_right:
                    lb_strength = pd.DataFrame({
                        'Type': ['1 Kæde', '2 Kæder', '3 Kæder'],
                        'Antal': [get_lb('oneLine'), get_lb('twoLines'), get_lb('threeLines')]
                    })
                    if lb_strength['Antal'].sum() > 0:
                        fig_strength = px.pie(lb_strength, values='Antal', names='Type', title="Linjer brudt pr. pass",
                                             hole=0.5, color_discrete_sequence=['#333333', '#888888', '#df003b'])
                        st.plotly_chart(fig_strength, use_container_width=True)
            else:
                st.info(f"Ingen linebreak-data fundet for {selected_name}.")
