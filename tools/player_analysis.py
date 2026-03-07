import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent data
    df_xg = dp.get("xg_agg")
    df_lb = dp.get("linebreaks")
    
    # Hent name_map og tving nøgler til små bogstaver og rens dem
    raw_name_map = dp.get("name_map", {})
    name_map = {str(k).strip().lower(): str(v).strip() for k, v in raw_name_map.items()}

    if df_xg is None or df_xg.empty:
        st.warning("Ingen xG-data fundet i Snowflake for den valgte periode.")
        return

    # 2. Forberedelse af data
    df_working = df_xg.copy()
    df_working['STAT_VALUE'] = pd.to_numeric(df_working['STAT_VALUE'], errors='coerce').fillna(0)
    
    # Tving PLAYER_OPTAUUID til string, små bogstaver og rens den
    df_working['PLAYER_OPTAUUID'] = df_working['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
    
    # 3. Pivotering
    pivot_stats = df_working.pivot_table(
        index='PLAYER_OPTAUUID', 
        columns='STAT_TYPE', 
        values='STAT_VALUE', 
        aggfunc='sum'
    ).fillna(0).reset_index()

    # Tving ID igen efter pivot for en sikkerheds skyld
    pivot_stats['PLAYER_OPTAUUID'] = pivot_stats['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
    
    # Map navne
    pivot_stats['NAVN'] = pivot_stats['PLAYER_OPTAUUID'].map(name_map)
    
    # Fallback hvis navnet mangler
    pivot_stats['NAVN'] = pivot_stats['NAVN'].fillna(pivot_stats['PLAYER_OPTAUUID'].apply(lambda x: f"Ukendt ({x[:5]})"))

    # 4. Beregn stats pr. 90 min
    if 'minsPlayed' in pivot_stats.columns:
        # Vi sikrer os mod division med 0 ved at bruge .clip(lower=1)
        mins = pivot_stats['minsPlayed'].clip(lower=1)
        
        if 'expectedGoals' in pivot_stats.columns:
            pivot_stats['xG_90'] = (pivot_stats['expectedGoals'] / mins * 90)
        
        if 'expectedAssists' in pivot_stats.columns:
            pivot_stats['xA_90'] = (pivot_stats['expectedAssists'] / mins * 90)
            
        if 'expectedGoalsNonpenalty' in pivot_stats.columns:
            pivot_stats['npxG_90'] = (pivot_stats['expectedGoalsNonpenalty'] / mins * 90)
    else:
        pivot_stats['xG_90'] = 0
        pivot_stats['xA_90'] = 0
        pivot_stats['npxG_90'] = 0

    # --- DEFINITION AF TABS (Skal ske før de bruges med 'with') ---
    tab_squad, tab_single, tab_lb = st.tabs([
        "TRUP OVERSIGT", 
        "INDIVIDUEL ANALYSE", 
        "LINEBREAKS"
    ])

    # --- 5. VISNING I TABELLEN ---
    with tab_squad:
        st.subheader("Leaderboard: Sæsonstatistik")
        
        # Kolonner der skal vises
        display_cols = [
            'NAVN', 'minsPlayed', 
            'expectedGoals', 'xG_90', 
            'expectedAssists', 'xA_90', 
            'expectedGoalsNonpenalty', 'npxG_90'
        ]
        final_cols = [c for c in display_cols if c in pivot_stats.columns]
        
        df_table = pivot_stats[final_cols].sort_values('expectedGoals', ascending=False)

        st.dataframe(
            df_table,
            column_config={
                "NAVN": st.column_config.TextColumn("Spiller"),
                "minsPlayed": st.column_config.NumberColumn("Minutter", format="%d"),
                "expectedGoals": st.column_config.NumberColumn("Total xG", format="%.2f"),
                "xG_90": st.column_config.NumberColumn("xG/90", format="%.2f"),
                "expectedGoalsNonpenalty": st.column_config.NumberColumn("npxG", format="%.2f"),
                "npxG_90": st.column_config.NumberColumn("npxG/90", format="%.2f"),
                "expectedAssists": st.column_config.NumberColumn("Total xA", format="%.2f"),
                "xA_90": st.column_config.NumberColumn("xA/90", format="%.2f")
            },
            use_container_width=True,
            hide_index=True
        )

    with tab_single:
        # Dropdown baseret på de navne vi lige har mappet
        sorted_pivot = pivot_stats.sort_values('NAVN')
        selected_name = st.selectbox(
            "Vælg Spiller", 
            options=sorted_pivot['NAVN'].tolist()
        )
        
        # Hent UUID baseret på valgt navn
        selected_uuid = sorted_pivot[sorted_pivot['NAVN'] == selected_name]['PLAYER_OPTAUUID'].values[0]

        # Metrics
        p_xg = df_working[df_working['PLAYER_OPTAUUID'] == selected_uuid]
        
        m1, m2, m3, m4 = st.columns(4)
        def get_v(stat): return p_xg[p_xg['STAT_TYPE'] == stat]['STAT_VALUE'].sum()

        m1.metric("Total xG", f"{get_v('expectedGoals'):.2f}")
        m2.metric("Non-Penalty xG", f"{get_v('expectedGoalsNonpenalty'):.2f}")
        m3.metric("Total xA", f"{get_v('expectedAssists'):.2f}")
        m4.metric("Minutter", int(get_v('minsPlayed')))

        # xG Fordeling Graf
        xg_cats = ['expectedGoalsHd', 'expectedGoalsOpenplay', 'expectedGoalsSetplay']
        xg_plot = p_xg[p_xg['STAT_TYPE'].isin(xg_cats)].groupby('STAT_TYPE')['STAT_VALUE'].sum().reset_index()
        
        if not xg_plot.empty and xg_plot['STAT_VALUE'].sum() > 0:
            fig_xg = px.bar(xg_plot, x='STAT_TYPE', y='STAT_VALUE', 
                            title=f"xG Fordeling: {selected_name}", 
                            color_discrete_sequence=['#df003b'])
            st.plotly_chart(fig_xg, use_container_width=True)

    # --- NY OPTIMERET LINEBREAK SEKTION ---
    with tab_lb:
        if df_lb is not None and not df_lb.empty:
            df_lb['PLAYER_OPTAUUID'] = df_lb['PLAYER_OPTAUUID'].astype(str).str.strip().str.lower()
            p_lb = df_lb[df_lb['PLAYER_OPTAUUID'] == selected_uuid].copy()
            
            if not p_lb.empty:
                # Konverter stats til tal
                for col in ['STAT_VALUE', 'STAT_FH', 'STAT_SH']:
                    p_lb[col] = pd.to_numeric(p_lb[col], errors='coerce').fillna(0)

                # Hjælpefunktion til at hente specifikke LB stats
                def get_lb(stat_type):
                    return p_lb[p_lb['STAT_TYPE'] == stat_type]['STAT_VALUE'].sum()

                # A. Top Metrics: Intensitet og Slutprodukt
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Linebreaks", int(get_lb('total')))
                m2.metric("Under Pres", int(get_lb('underPressure')))
                m3.metric("Farlige (Danger)", int(get_lb('leadingToDanger')))
                m4.metric("Til Skud", int(get_lb('leadingToShots')))

                st.markdown("---")

                # B. Visualisering 1: Hvilke kæder brydes (Zone-fordeling)
                # Vi bruger dine data: attackingLineBroken, midfieldLineBroken, defenceLineBroken
                col_left, col_right = st.columns(2)

                with col_left:
                    lb_zones = pd.DataFrame({
                        'Kæde': ['Modstander Forsvar', 'Midtbane', 'Angreb/Pres'],
                        'Antal': [
                            get_lb('attackingLineBroken'), 
                            get_lb('midfieldLineBroken'), 
                            get_lb('defenceLineBroken')
                        ]
                    })
                    fig_zones = px.bar(
                        lb_zones, x='Antal', y='Kæde', orientation='h',
                        title="Gennembrud pr. kæde",
                        color='Kæde',
                        color_discrete_map={
                            'Modstander Forsvar': '#df003b', 
                            'Midtbane': '#b8860b', 
                            'Angreb/Pres': '#333333'
                        }
                    )
                    fig_zones.update_layout(showlegend=False)
                    st.plotly_chart(fig_zones, use_container_width=True)

                with col_right:
                    # C. Visualisering 2: Gennembrudsstyrke (oneLine vs twoLines vs threeLines)
                    lb_strength = pd.DataFrame({
                        'Type': ['1 Kæde', '2 Kæder', '3 Kæder'],
                        'Antal': [get_lb('oneLine'), get_lb('twoLines'), get_lb('threeLines')]
                    })
                    fig_strength = px.pie(
                        lb_strength, values='Antal', names='Type',
                        title="Linjer brudt pr. aflevering",
                        hole=0.5,
                        color_discrete_sequence=['#333333', '#888888', '#df003b']
                    )
                    st.plotly_chart(fig_strength, use_container_width=True)

                # D. Halvlegs-sammenligning (Din originale bar, men med alle typer)
                st.markdown("---")
                lb_types = ['defenceLineBroken', 'midfieldLineBroken', 'attackingLineBroken']
                lb_halves = p_lb[p_lb['STAT_TYPE'].isin(lb_types)]
                
                fig_halves = px.bar(
                    lb_halves, y='STAT_TYPE', x=['STAT_FH', 'STAT_SH'],
                    orientation='h', title="Præstation over tid (1. vs 2. halvleg)",
                    color_discrete_map={'STAT_FH': '#b8860b', 'STAT_SH': '#df003b'},
                    labels={'value': 'Antal linjebrud', 'STAT_TYPE': 'Type'}
                )
                st.plotly_chart(fig_halves, use_container_width=True)
                
            else:
                st.info(f"Ingen linebreak-data fundet for {selected_name}.")
