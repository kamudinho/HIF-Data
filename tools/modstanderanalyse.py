import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
from data.data_load import load_snowflake_query

def vis_side(df_team_matches, hold_map):
    # --- 1. FARVER & SETUP ---
    HIF_ROD = "#df003b"
    HIF_GOLD = "#b8860b"
    
    # --- 2. DATA LOAD (Optimering) ---
    if "events_data" not in st.session_state:
        with st.spinner("Henter detaljeret kamp-data..."):
            dp = st.session_state["data_package"]
            # Vi gemmer direkte i session_state
            st.session_state["events_data"] = load_snowflake_query(
                "events", dp["comp_filter"], dp["season_filter"]
            )
    
    df_events = st.session_state["events_data"]

    # --- 3. TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:{HIF_ROD}; padding:15px; border-radius:10px; margin-bottom:20px; border-left: 8px solid {HIF_GOLD};">
            <h2 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:2px;">
                Modstanderanalyse: {st.session_state.get('valgt_modstander_navn', 'Vælg hold')}
            </h2>
        </div>
    """, unsafe_allow_html=True)

    # --- 4. FILTRERING (Dropdowns) ---
    col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])
    
    with col_sel1:
        comp_options = df_team_matches[['COMPETITION_NAME', 'COMPETITION_WYID']].drop_duplicates()
        comp_dict = dict(zip(comp_options['COMPETITION_NAME'], comp_options['COMPETITION_WYID']))
        valgt_comp_navn = st.selectbox("Turnering:", options=sorted(comp_dict.keys()))
        valgt_comp_id = comp_dict[valgt_comp_navn]

    # Filtrer hold
    df_filtered_comp = df_team_matches[df_team_matches['COMPETITION_WYID'] == valgt_comp_id]
    navne_dict = {hold_map.get(tid, f"Hold {tid}"): tid for tid in df_filtered_comp['TEAM_WYID'].unique()}
    
    with col_sel2:
        valgt_hold_navn = st.selectbox("Modstander:", options=sorted(navne_dict.keys()))
        valgt_hold_id = navne_dict[valgt_hold_navn]
        st.session_state['valgt_modstander_navn'] = valgt_hold_navn # Bruges til overskrift
        
    with col_sel3:
        halvdel = st.radio("Fokus på banehalvdel:", ["Defensiv", "Offensiv"], horizontal=True)

    df_hold_data = df_filtered_comp[df_filtered_comp['TEAM_WYID'] == valgt_hold_id].copy()

    # --- 5. STATS (Metrics) ---
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Mål pr. kamp", round(df_hold_data['GOALS'].mean(), 1))
    with m2: st.metric("xG pr. kamp", round(df_hold_data['XG'].mean(), 2))
    with m3: st.metric("Skud", round(df_hold_data['SHOTS'].mean(), 1))
    with m4: st.metric("Skud imod", round(df_hold_data['SHOTS_AGAINST'].mean(), 1) if 'SHOTS_AGAINST' in df_hold_data else "N/A")

    st.divider()

    # --- 6. VISUAL ANALYSE (Heatmaps) ---
    main_col, side_col = st.columns([2.5, 1])

    with main_col:
        # Vi bruger Wyscout-banen som i din oprindelige kode
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#fdfdfd', line_color='#333', half=True)
        c1, c2, c3 = st.columns(3)
        
        # Filtrer events for det valgte hold
        df_hold_ev = df_events[df_events['TEAM_WYID'] == valgt_hold_id].copy()

        if not df_hold_ev.empty:
            # Logik for banehalvdel
            if halvdel == "Offensiv":
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50]
            else:
                # Ved defensiv spejler vi banen så vi ser deres forsvarsaktioner i toppen
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
                df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

            event_configs = [
                (c1, "Passes", "pass", "Reds"),
                (c2, "Def. Duels", "duel", "Blues"),
                (c3, "Recoveries", "interception", "Greens")
            ]

            for col, title, p_type, cmap in event_configs:
                with col:
                    st.caption(f"**{title} Density**")
                    fig, ax = pitch.draw(figsize=(4, 5))
                    df_f = df_plot[df_plot['PRIMARYTYPE'].str.contains(p_type, case=False, na=False)]
                    
                    if not df_f.empty:
                        # Vi bruger fill=True og levels for et mere "flydende" look
                        sns.kdeplot(x=df_f['LOCATIONY'], y=df_f['LOCATIONX'], ax=ax, 
                                    fill=True, cmap=cmap, alpha=0.6, levels=8, thresh=0.1)
                    else:
                        ax.text(50, 75, "Ingen data", ha='center', color='gray')
                    st.pyplot(fig)

    with side_col:
        st.subheader("Seneste Form")
        if not df_hold_data.empty:
            df_display = df_hold_data.sort_values('DATE', ascending=False).head(5)
            # Formater MATCHLABEL pænt
            df_display['KAMP'] = df_display['MATCHLABEL'].str.replace(',', ' -')
            st.dataframe(
                df_display[['DATE', 'KAMP']], 
                hide_index=True, 
                use_container_width=True
            )
