import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING ---
    df_xg = dp.get("xg_agg", pd.DataFrame())
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    df_shots = dp.get("playerstats", pd.DataFrame())
    df_matches = dp.get("matches", pd.DataFrame()) # Vi bruger denne til holdnavne
    name_map = dp.get("name_map", {})
    
    # Hent valgte parametre til titler (hvis de findes i session_state)
    saeson_f = st.session_state.get('saeson_f', 'Valgt Sæson')

    if df_xg.empty:
        st.warning("⚠️ Ingen data fundet. Tjek filtre eller Snowflake forbindelse.")
        return

    # --- 2. DATA CLEANING & HOLD-MAPPING ---
    df_xg.columns = [c.upper() for c in df_xg.columns]
    player_col = 'PLAYER_OPTAUUID'
    team_col = 'CONTESTANT_OPTAUUID'
    
    # Lav en lynhurtig mapping af Team UUID -> Holdnavn fra matchinfo
    team_map = {}
    if not df_matches.empty:
        df_matches.columns = [c.upper() for c in df_matches.columns]
        # Vi mapper både hjemme og udehold for at være sikre
        for _, row in df_matches.iterrows():
            team_map[row['CONTESTANTHOME_OPTAUUID']] = row['CONTESTANTHOME_NAME']
            team_map[row['CONTESTANTAWAY_OPTAUUID']] = row['CONTESTANTAWAY_NAME']

    # --- 3. PIVOTERING (xG og xA) ---
    pivot_stats = df_xg.pivot_table(
        index=[player_col, team_col], 
        columns='STAT_TYPE', 
        values='STAT_VALUE',
        aggfunc='sum'
    ).fillna(0).reset_index()

    # SIKRING af kolonner
    for col in ['expectedGoals', 'expectedAssists']:
        if col not in pivot_stats.columns:
            pivot_stats[col] = 0.0

    # Navne og Holdnavne
    pivot_stats[player_col] = pivot_stats[player_col].astype(str).str.strip().str.lower()
    pivot_stats['NAVN'] = pivot_stats[player_col].map(name_map).fillna(pivot_stats[player_col])
    pivot_stats['HOLD'] = pivot_stats[team_col].map(team_map).fillna("Ukendt Hold")

    # --- 4. TABS ---
    tab_squad, tab_single, tab_lb = st.tabs(["HOLDOVERSIGT", "SPILLERPERFORMANCE", "LINEBREAKS"])

    with tab_squad:
        st.subheader(f"Top Performance - {saeson_f}")
        
        # Vi tilføjer HOLD kolonnen her, så det er nemt at se hvem der spiller hvor
        display_df = pivot_stats[['NAVN', 'HOLD', 'expectedGoals', 'expectedAssists']].sort_values('expectedGoals', ascending=False)
        
        # Formatering til 2 decimaler
        st.dataframe(
            display_df.style.format({'expectedGoals': '{:.2f}', 'expectedAssists': '{:.2f}'}),
            use_container_width=True, hide_index=True
        )

    with tab_single:
        # Selectbox med både Navn og Hold (så vi kan kende forskel på to spillere med samme navn)
        pivot_stats['SELECT_NAME'] = pivot_stats['NAVN'] + " (" + pivot_stats['HOLD'] + ")"
        all_names = sorted(pivot_stats['SELECT_NAME'].unique())
        selected_display = st.selectbox("Vælg spiller", options=all_names, key="sb_performance")
        
        # Find data for den valgte
        p_row = pivot_stats[pivot_stats['SELECT_NAME'] == selected_display].iloc[0]
        selected_uuid = p_row[player_col]

        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total xG", f"{p_row['expectedGoals']:.2f}")
        m2.metric("Total xA", f"{p_row['expectedAssists']:.2f}")
        
        # Skud-data (hvis tilgængelig)
        if not df_shots.empty:
            df_shots.columns = [c.upper() for c in df_shots.columns]
            p_shots = df_shots[df_shots[player_col].astype(str).str.lower() == selected_uuid]
            
            if 'EVENT_X' in p_shots.columns:
                is_dz = (p_shots['EVENT_X'] >= 88.5) & (p_shots['EVENT_Y'].between(37, 63))
                m4.metric("Skud i DZ", int(is_dz.sum()))
            else:
                m3.metric("Skud i alt", len(p_shots))
                m4.metric("Skud i DZ", "N/A")

        # Plot over hele ligaen (markér den valgte spiller)
        fig = px.scatter(pivot_stats, x='expectedAssists', y='expectedGoals', 
                         hover_name='NAVN', color='HOLD',
                         labels={'expectedAssists': 'xA', 'expectedGoals': 'xG'},
                         title=f"xG vs xA i Ligaen")
        st.plotly_chart(fig, use_container_width=True)

    with tab_lb:
        if not df_lb.empty:
            df_lb.columns = [c.upper() for c in df_lb.columns]
            # Filtrér linebreaks på spillerens UUID
            p_lb_data = df_lb[df_lb[player_col].astype(str).str.lower() == selected_uuid]
            
            if not p_lb_data.empty:
                st.write(f"Linebreak analyse for **{p_row['NAVN']}**")
                # Pivotér linebreaks så de er nemme at læse
                lb_pivot = p_lb_data.groupby('STAT_TYPE')['STAT_TOTAL'].sum().reset_index()
                st.dataframe(lb_pivot, use_container_width=True, hide_index=True)
            else:
                st.info(f"Ingen linebreaks fundet for denne spiller.")
        else:
            st.info("Ingen linebreak-data tilgængelig.")
