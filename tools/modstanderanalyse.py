import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch

def vis_side(df_team_matches, hold_map, df_events):
    # --- 1. CSS STYLING AF METRICS ---
    st.markdown("""
        <style>
            [data-testid="stMetric"] {
                background-color: #ffffff; padding: 15px; border-radius: 10px; 
                border-bottom: 4px solid #cc0000; box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. FILTRERING ---
    # Vi finder de unikke turneringer i din team_matches DF
    turneringer = sorted(df_team_matches['COMPETITION_WYID'].unique())
    col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])
    
    with col_sel1:
        valgt_comp = st.selectbox("Turnering:", options=turneringer)
    
    df_filtered = df_team_matches[df_team_matches['COMPETITION_WYID'] == valgt_comp]
    
    # Mapper holdnavne via dit hold_map
    navne_dict = {hold_map.get(str(int(tid)), f"Hold {tid}"): tid for tid in df_filtered['TEAM_WYID'].unique()}
    
    with col_sel2:
        valgt_navn = st.selectbox("Modstander:", options=sorted(navne_dict.keys()))
    with col_sel3:
        halvdel = st.radio("Fokus:", ["Modstander", "Egen"], horizontal=True)

    # Her defineres den variabel, der drillede før
    valgt_id = navne_dict[valgt_navn]
    df_hold_matches = df_filtered[df_filtered['TEAM_WYID'] == valgt_id].copy()

    # --- 3. STATISTISK OVERBLIK (METRICS) ---
    st.subheader(f"Statistisk overblik: {valgt_navn}")
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        val = round(df_hold_matches['GOALS'].mean(), 1) if 'GOALS' in df_hold_matches.columns else 0.0
        st.metric("GNS. MÅL", val)
    with m2:
        # Vi tjekker efter både XG (fra din nye join) og XGSHOT (fra spiller-stats)
        xg_col = 'XG' if 'XG' in df_hold_matches.columns else ('XGSHOT' if 'XGSHOT' in df_hold_matches.columns else None)
        val = round(df_hold_matches[xg_col].mean(), 2) if xg_col else 0.0
        st.metric("GNS. XG", val)
    with m3:
        val = round(df_hold_matches['SHOTS'].mean(), 1) if 'SHOTS' in df_hold_matches.columns else 0.0
        st.metric("SKUD PR. KAMP", val)
    with m4:
        poss = df_hold_matches['POSSESSIONPERCENT'].mean() if 'POSSESSIONPERCENT' in df_hold_matches.columns else None
        st.metric("POSSESSION", f"{int(poss)}%" if poss else "N/A")

    st.markdown("---")

    # --- 4. HEATMAPS OG KAMP-LOG ---
    main_col, side_col = st.columns([3, 1])

    with main_col:
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#f8f9fa', line_color='#333', half=True)
        c1, c2, c3 = st.columns(3)
        
        # Filtrering af events baseret på det valgte hold
        target_id_str = str(int(valgt_id))
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
                        sns.kdeplot(x=df_f['LOCATIONY'], y=df_f['LOCATIONX'], ax=ax, fill=True, cmap=cmap, alpha=0.7, levels=10)
                    else:
                        ax.text(50, 75, "Ingen data", ha='center', va='center', color='gray')
                    st.pyplot(fig, use_container_width=True)
        else:
            st.warning(f"Ingen hændelsesdata fundet for {valgt_navn} (ID: {valgt_id})")

    with side_col:
        st.write("**Seneste kampe**")
        cols_to_show = [c for c in ['DATE', 'STATUS', 'GAMEWEEK'] if c in df_hold_matches.columns]
        st.dataframe(df_hold_matches[cols_to_show].sort_values('DATE', ascending=False), hide_index=True)
