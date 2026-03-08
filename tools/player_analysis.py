import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. HENT DATA (Vi bruger de nøgler, din opta_queries.py leverer) ---
    df_xg = dp.get("opta_expected_goals")
    df_lb = dp.get("opta_linebreaks")
    df_shots = dp.get("opta_shotevents")
    df_quals = dp.get("opta_qualifiers")
    
    raw_name_map = dp.get("name_map", {})
    name_map = {str(k).strip().lower(): str(v).strip() for k, v in raw_name_map.items()}

    # Tjek om xG-data overhovedet er landet i funktionen
    if df_xg is None or df_xg.empty:
        st.warning("⚠️ Data modtaget, men 'opta_expected_goals' er tom. Tjek liga/sæson-valg.")
        return

    # --- 2. ROBUST KOLONNE-RENSNING ---
    # Vi tvinger alle kolonnenavne til UPPERCASE for at matche din logik herunder
    df_xg.columns = [c.upper() for c in df_xg.columns]
    
    df_working = df_xg.copy()
    df_working['STAT_VALUE'] = pd.to_numeric(df_working['STAT_VALUE'], errors='coerce').fillna(0)
    df_working['PLAYER_OPTAUUID'] = df_working['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
    
    if df_shots is not None and not df_shots.empty:
        df_shots.columns = [c.upper() for c in df_shots.columns]
        df_shots['PLAYER_OPTAUUID'] = df_shots['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()

    if df_quals is not None and not df_quals.empty:
        df_quals.columns = [c.upper() for c in df_quals.columns]

    # --- 3. PIVOTERING ---
    # Vi sikrer os at de nødvendige kolonner findes før pivot
    needed = {'PLAYER_OPTAUUID', 'STAT_TYPE', 'STAT_VALUE'}
    if not needed.issubset(df_working.columns):
        st.error(f"Manglende kolonner i xG data. Fundet: {df_working.columns.tolist()}")
        return

    pivot_stats = df_working.pivot_table(
        index='PLAYER_OPTAUUID', 
        columns='STAT_TYPE', 
        values='STAT_VALUE', 
        aggfunc='sum'
    ).fillna(0).reset_index()
    
    pivot_stats['NAVN'] = pivot_stats['PLAYER_OPTAUUID'].map(name_map)
    pivot_stats['NAVN'] = pivot_stats['NAVN'].fillna(pivot_stats['PLAYER_OPTAUUID'].apply(lambda x: f"Ukendt ({x[:5]})"))

    # --- 4. DANGER ZONE LOGIK (Kobling af Shots + Quals) ---
    if df_shots is not None and not df_shots.empty and df_quals is not None:
        danger_ids = [16, 17, '16', '17']
        # Finder alle unikke skud-ID'er der har de rigtige qualifiers
        dz_events = df_quals[df_quals['QUALIFIER_QID'].astype(str).isin(['16', '17'])]['EVENT_OPTAUUID'].unique()
        df_shots['IS_DZ'] = df_shots['EVENT_OPTAUUID'].isin(dz_events)

    # --- 5. TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["OVERSIGT", "INDIVIDUEL ANALYSE", "LINEBREAKS"])

    with tab_squad:
        # Sørg for at vi kun prøver at vise kolonner der findes
        cols_to_show = ['NAVN', 'expectedGoals', 'expectedAssists', 'minsPlayed']
        existing_cols = [c for c in cols_to_show if c in pivot_stats.columns]
        st.dataframe(pivot_stats[existing_cols].sort_values('expectedGoals', ascending=False), 
                     use_container_width=True, hide_index=True)
        
    with tab_single:
        sorted_pivot = pivot_stats.sort_values('NAVN')
        selected_name = st.selectbox("Vælg Spiller", options=sorted_pivot['NAVN'].tolist())
        selected_uuid = sorted_pivot[sorted_pivot['NAVN'] == selected_name]['PLAYER_OPTAUUID'].values[0]

        # DZ Tæller
        dz_total = 0
        if df_shots is not None and 'IS_DZ' in df_shots.columns:
            p_dz = df_shots[(df_shots['PLAYER_OPTAUUID'] == selected_uuid) & (df_shots['IS_DZ'] == True)]
            dz_total = len(p_dz)

        # Metrics
        p_xg_indiv = df_working[df_working['PLAYER_OPTAUUID'] == selected_uuid]
        def get_v(stat): 
            return p_xg_indiv[p_xg_indiv['STAT_TYPE'] == stat]['STAT_VALUE'].sum() if not p_xg_indiv.empty else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total xG", f"{get_v('expectedGoals'):.2f}")
        m2.metric("Total xA", f"{get_v('expectedAssists'):.2f}")
        m3.metric("Skud i DZ", dz_total, help="Skud fra Q16 (Box-C) eller Q17 (Small Box-C)")
        
        # Skud i alt
        total_shots = len(df_shots[df_shots['PLAYER_OPTAUUID'] == selected_uuid]) if df_shots is not None else 0
        m4.metric("Skud i alt", total_shots)

        st.markdown("---")
        # Grafer her...

    # (Linebreaks fanen fortsætter herfra med samme indrykning som tab_single)
        # Her kan du indsætte xG-graferne igen

    with tab_lb:
        if df_lb is not None and not df_lb.empty:
            df_lb['PLAYER_OPTAUUID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
            p_lb = df_lb[df_lb['PLAYER_OPTAUUID'] == selected_uuid].copy()
            
            if not p_lb.empty:
                for col in ['STAT_VALUE', 'STAT_FH', 'STAT_SH']:
                    if col in p_lb.columns:
                        p_lb[col] = pd.to_numeric(p_lb[col], errors='coerce').fillna(0)

                def get_lb(stat_type):
                    return p_lb[p_lb['STAT_TYPE'] == stat_type]['STAT_VALUE'].sum()

                # Metrics for Linebreaks
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Linebreaks", int(get_lb('total')))
                m2.metric("Under Pres", int(get_lb('underPressure')))
                m3.metric("Farlige", int(get_lb('leadingToDanger')))
                m4.metric("Til Skud", int(get_lb('leadingToShots')))

                st.markdown("---")
                
                col_left, col_right = st.columns(2)
                with col_left:
                    lb_zones = pd.DataFrame({
                        'Kæde': ['Forsvar', 'Midtbane', 'Angreb'],
                        'Antal': [get_lb('attackingLineBroken'), get_lb('midfieldLineBroken'), get_lb('defenceLineBroken')]
                    })
                    fig_zones = px.bar(lb_zones, x='Antal', y='Kæde', orientation='h', title="Hvilke kæder brydes?",
                                       color='Kæde', color_discrete_map={'Forsvar': '#df003b', 'Midtbane': '#b8860b', 'Angreb': '#333333'})
                    st.plotly_chart(fig_zones, use_container_width=True)

                with col_right:
                    lb_strength = pd.DataFrame({
                        'Type': ['1 Kæde', '2 Kæder', '3 Kæder'],
                        'Antal': [get_lb('oneLine'), get_lb('twoLines'), get_lb('threeLines')]
                    })
                    fig_strength = px.pie(lb_strength, values='Antal', names='Type', title="Linjer brudt pr. pass",
                                         hole=0.5, color_discrete_sequence=['#333333', '#888888', '#df003b'])
                    st.plotly_chart(fig_strength, use_container_width=True)
            else:
                st.info(f"Ingen linebreak-data fundet for {selected_name}.")
        else:
            st.error("Linebreak-data mangler.")
