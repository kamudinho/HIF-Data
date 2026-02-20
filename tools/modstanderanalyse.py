import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
from data.data_load import load_snowflake_query

def vis_side(df_team_matches, hold_map, df_events=None):
    st.write("### Modstanderanalyse")

    if "events_data" not in st.session_state:
        st.info("Denne analyse kræver detaljeret kamp-data (events).")
        
        # Hent filtre fra session_state (fra din data_package)
        dp = st.session_state["data_package"]
        
        if st.button("🚀 Hent hændelses-data fra Snowflake"):
            with st.spinner("Henter hændelser (afleveringer, dueller osv.)..."):
                # Vi henter kun query'en "events"
                st.session_state["events_data"] = load_snowflake_query(
                    "events", dp["comp_filter"], dp["season_filter"]
                )
                st.rerun()
        return # Stop her indtil data er hentet

    # Definer df_events fra session_state, når de ER hentet
    df_events = st.session_state["events_data"]
    
    # FØRST HER henter vi de tunge event-data
    if st.button("Hent detaljeret event-data (tager et øjeblik)"):
        events = load_snowflake_query("events", st.session_state.comp_filter, st.session_state.season_filter)
        
    # --- 1. CSS STYLING ---
    st.markdown("""
        <style>
            [data-testid="stMetric"] {
                background-color: #ffffff; padding: 15px; border-radius: 10px; 
                border-bottom: 4px solid #cc0000; box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DROPDOWNS OG FILTRERING ---
    if 'COMPETITION_NAME' in df_team_matches.columns:
        comp_options = df_team_matches[['COMPETITION_NAME', 'COMPETITION_WYID']].drop_duplicates()
        comp_dict = dict(zip(comp_options['COMPETITION_NAME'], comp_options['COMPETITION_WYID']))
        
        col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])
        with col_sel1:
            valgt_comp_navn = st.selectbox("Vælg Turnering:", options=sorted(comp_dict.keys()))
            valgt_comp_id = comp_dict[valgt_comp_navn]
    else:
        turneringer = sorted(df_team_matches['COMPETITION_WYID'].unique())
        col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])
        with col_sel1:
            valgt_comp_id = st.selectbox("Vælg Turnering (ID):", options=turneringer)

    # Filtrer hold baseret på turnering
    df_filtered_comp = df_team_matches[df_team_matches['COMPETITION_WYID'] == valgt_comp_id]
    
    # Lav navne_dict (Sikrer at hold-navne vises korrekt)
    navne_dict = {}
    for tid in df_filtered_comp['TEAM_WYID'].unique():
        tid_str = str(int(tid))
        navn = hold_map.get(tid_str, f"Hold {tid_str}")
        navne_dict[navn] = tid
    
    with col_sel2:
        valgt_hold_navn = st.selectbox("Vælg Modstander:", options=sorted(navne_dict.keys()))
        valgt_hold_id = navne_dict[valgt_hold_navn]
        
    with col_sel3:
        halvdel = st.radio("Fokus:", ["Modstander", "Egen"], horizontal=True)

    df_hold_data = df_filtered_comp[df_filtered_comp['TEAM_WYID'] == valgt_hold_id].copy()

    # --- 3. STATISTISK OVERBLIK ---
    st.subheader(f"Statistisk overblik: {valgt_hold_navn}")
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        st.metric("GNS. MÅL", round(df_hold_data['GOALS'].mean(), 1) if 'GOALS' in df_hold_data else 0.0)
    with m2:
        st.metric("GNS. XG", round(df_hold_data['XG'].mean(), 2) if 'XG' in df_hold_data else 0.0)
    with m3:
        st.metric("SKUD PR. KAMP", round(df_hold_data['SHOTS'].mean(), 1) if 'SHOTS' in df_hold_data else 0.0)
    with m4:
        st.metric("SKUD PÅ MÅL", round(df_hold_data['SHOTSONTARGET'].mean(), 1) if 'SHOTSONTARGET' in df_hold_data else 0.0)

    st.markdown("---")

    # --- 4. HEATMAPS OG KAMP-LISTE ---
    main_col, side_col = st.columns([3, 1])

    with main_col:
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#f8f9fa', line_color='#333', half=True)
        c1, c2, c3 = st.columns(3)
        
        target_id_str = str(int(valgt_hold_id))
        df_hold_ev = df_events[df_events['TEAM_WYID'].astype(str).str.contains(target_id_str)].copy()

        if not df_hold_ev.empty:
            if halvdel == "Modstander":
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50]
            else:
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
                df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

            plots = [
                (c1, "Afleveringer", "pass", "Reds"), 
                (c2, "Dueller", "duel", "Blues"), 
                (c3, "Erobringer", "interception", "Greens")
            ]
            
            for col, title, p_type, cmap in plots:
                with col:
                    st.write(f"**{title}**")
                    fig, ax = pitch.draw(figsize=(4, 5))
                    mask = df_plot['PRIMARYTYPE'].str.contains(p_type, case=False, na=False)
                    df_f = df_plot[mask]
                    
                    if not df_f.empty:
                        sns.kdeplot(
                            x=df_f['LOCATIONY'], y=df_f['LOCATIONX'], ax=ax, 
                            fill=True, cmap=cmap, alpha=0.7, levels=10,
                            thresh=0.05, clip=((0, 100), (50, 100))
                        )
                        ax.set_xlim(0, 100)
                        ax.set_ylim(50, 100)
                    else:
                        ax.text(50, 75, "Ingen data", ha='center', va='center', color='gray')
                    st.pyplot(fig, use_container_width=True)
        else:
            st.warning(f"Ingen hændelsesdata fundet for {valgt_hold_navn}")

    with side_col:
        st.write("**Seneste kampe**")
        cols_vis = [c for c in ['DATE', 'MATCHLABEL', 'GAMEWEEK'] if c in df_hold_data.columns]
        if not df_hold_data.empty:
            st.dataframe(df_hold_data[cols_vis].sort_values('DATE', ascending=False), hide_index=True)
