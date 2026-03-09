import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING ---
    df_xg = dp.get("xg_agg", pd.DataFrame())
    df_lb = dp.get("player_linebreaks", pd.DataFrame())
    df_shots = dp.get("playerstats", pd.DataFrame())
    name_map = dp.get("name_map", {})

    if df_xg.empty:
        st.warning("Ingen data fundet for Hvidovre IF i xG-tabellen.")
        return

    # --- 2. DATA CLEANING ---
    df_xg.columns = [c.upper() for c in df_xg.columns]
    df_working = df_xg.copy()
    
    player_col = 'PLAYER_OPTAUUID'
    stat_type_col = 'STAT_TYPE'
    stat_val_col = 'STAT_VALUE'

    # --- 3. PIVOTERING & ENSRETNING ---
    pivot_stats = df_working.pivot_table(
        index=player_col, 
        columns=stat_type_col, 
        values=stat_val_col,
        aggfunc='sum'
    ).fillna(0).reset_index()

    # Mapping af Opta-specifikke navne (fx expectedGoalsNonpenalty)
    rename_rules = {
        'expectedGoalsNonpenalty': 'expectedGoals',
        'expectedAssistsOpenplay': 'expectedAssists'
    }
    for old, new in rename_rules.items():
        if old in pivot_stats.columns and new not in pivot_stats.columns:
            pivot_stats[new] = pivot_stats[old]

    # Sikr at kolonnerne findes (vigtigt for at undgå tomme tabeller)
    cols_to_ensure = ['expectedGoals', 'expectedAssists', 'minsPlayed', 'touches']
    for col in cols_to_ensure:
        if col not in pivot_stats.columns:
            pivot_stats[col] = 0.0

    # Navne-mapping (UUID -> Spiller Navn)
    pivot_stats['NAVN'] = pivot_stats[player_col].map(name_map).fillna(pivot_stats[player_col])

    # --- 4. VISNING (INGEN IKONER) ---
    st.title("Hvidovre IF - Spillere")
    
    tab_squad, tab_single, tab_lb = st.tabs(["Trupoversigt", "Individuel Performance", "Linebreaks"])

    with tab_squad:
        st.subheader("Truppen - Sæson Performance")
        # Oversigtstabel med alle spillere og deres xG/xA data
        display_df = pivot_stats[['NAVN', 'minsPlayed', 'expectedGoals', 'expectedAssists', 'touches']].sort_values('expectedGoals', ascending=False)
        
        st.dataframe(
            display_df.style.format({
                'expectedGoals': '{:.2f}', 
                'expectedAssists': '{:.2f}', 
                'minsPlayed': '{:.0f}',
                'touches': '{:.0f}'
            }), 
            use_container_width=True, hide_index=True
        )

    with tab_single:
        # Her kan du vælge enhver spiller fra truppen og se deres data
        all_names = sorted(pivot_stats['NAVN'].unique())
        selected_name = st.selectbox("Vælg spiller for detaljeret xG/xA", options=all_names, key="sb_player_perf")
        
        # Hent data for den valgte spiller
        p_row = pivot_stats[pivot_stats['NAVN'] == selected_name].iloc[0]
        p_uuid = p_row[player_col]

        # Visning af de individuelle stats
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Minutter", int(p_row['minsPlayed']))
        m2.metric("Total xG", f"{p_row['expectedGoals']:.2f}")
        m3.metric("Total xA", f"{p_row['expectedAssists']:.2f}")
        m4.metric("Touches", int(p_row['touches']))

        # Graf der viser spillerens placering i truppen
        fig = px.scatter(pivot_stats, x='expectedAssists', y='expectedGoals', 
                         hover_name='NAVN', size='minsPlayed',
                         text='NAVN',
                         color='expectedGoals', color_continuous_scale='Reds',
                         labels={'expectedAssists': 'xA', 'expectedGoals': 'xG'},
                         title=f"xG vs xA Fordeling i Truppen")
        fig.update_traces(textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

    with tab_lb:
        st.subheader(f"Linebreaks for {selected_name}")
        
        if not df_lb.empty:
            # 1. Standardiser alle kolonner til store bogstaver
            df_lb.columns = [c.upper() for c in df_lb.columns]
            
            # 2. Find den rigtige spiller-kolonne (Opta UUID kan variere i navnet)
            possible_id_cols = ['PLAYER_OPTAUUID', 'PLAYER_UUID', 'PLAYER_ID', 'PLAYERID']
            lb_id_col = next((c for c in possible_id_cols if c in df_lb.columns), None)

            if lb_id_col:
                # Filtrer på spilleren
                p_lb_data = df_lb[df_lb[lb_id_col] == p_uuid]
                
                if not p_lb_data.empty:
                    # Tjek om STAT_TYPE og STAT_TOTAL findes
                    type_col = 'STAT_TYPE' if 'STAT_TYPE' in p_lb_data.columns else None
                    val_col = 'STAT_TOTAL' if 'STAT_TOTAL' in p_lb_data.columns else 'STAT_VALUE'

                    if type_col and val_col in p_lb_data.columns:
                        lb_summary = p_lb_data.groupby(type_col)[val_col].sum().reset_index()
                        
                        # Vis grafen
                        st.bar_chart(lb_summary.set_index(type_col))
                        
                        # Vis rådata i en tabel under grafen
                        st.dataframe(p_lb_data[[type_col, val_col]], use_container_width=True, hide_index=True)
                    else:
                        st.warning("Data findes, men kolonne-formattet (STAT_TYPE/TOTAL) matcher ikke.")
                else:
                    st.info(f"Ingen registrerede linebreaks for {selected_name} i denne kamp/sæson.")
            else:
                st.error("Kunne ikke finde en spiller-ID kolonne i linebreak-data.")
                st.write("Tilgængelige kolonner:", list(df_lb.columns))
        else:
            st.info("Linebreak-data er tom (df_lb er empty).")
