import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch

try:
    from data.season_show import COMP_MAP
except ImportError:
    COMP_MAP = {}

def vis_side(df_team_matches, hold_map, df_events):
    # --- 1. CSS STYLING (Justering af placering) ---
    st.markdown("""
        <style>
            /* Vi fjerner den negative margin for at få banerne ned på plads */
            div[data-testid="stHorizontalBlock"] {
                gap: 1rem !important;
                margin-top: 10px !important; 
            }
            .stMetric { 
                background-color: #ffffff; padding: 10px; border-radius: 8px; 
                border-bottom: 3px solid #df003b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
            }
        </style>
    """, unsafe_allow_html=True)

    if df_team_matches is None or df_team_matches.empty:
        st.error("Kunne ikke finde kampdata.")
        return

    # --- 2. DROPDOWNS ---
    aktive_comp_ids = sorted(df_team_matches['COMPETITION_WYID'].unique()) if 'COMPETITION_WYID' in df_team_matches.columns else []

    col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])

    with col_sel1:
        valgt_comp_id = st.selectbox("Turnering:", options=aktive_comp_ids,
                                    format_func=lambda x: COMP_MAP.get(int(x), f"Turnering {x}"))

    df_comp = df_team_matches[df_team_matches['COMPETITION_WYID'] == valgt_comp_id]
    tilgaengelige_hold_ids = df_comp['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_hold_ids}
    
    with col_sel2:
        valgt_navn = st.selectbox("Modstander:", options=sorted(navne_dict.keys()))
    
    with col_sel3:
        halvdel = st.radio("Fokus:", ["Modstander", "Egen"], horizontal=True)

    valgt_id = navne_dict[valgt_navn]

    # --- 3. HEATMAPS (Rettet logik) ---
    st.markdown(f"### Analyse: {valgt_navn}") # Overskrift der skubber banerne lidt ned
    
    main_left, main_right = st.columns([2.8, 1])

    with main_left:
        # Vi giver banerne lidt pad (0.5) så de ikke klistrer til kanten
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#f8f9fa', line_color='#333', 
                              half=True, pad_top=0.5, pad_bottom=0.5)
        
        c1, c2, c3 = st.columns(3)

        # DEBUG: Tjek om der er data
        if df_events is not None and not df_events.empty:
            # Vi tvinger både kolonne og ID til string for at matche 100%
            df_hold_ev = df_events[df_events['TEAM_WYID'].astype(str).str.contains(str(int(valgt_id)))].copy()
            
            if df_hold_ev.empty:
                st.warning(f"Ingen events fundet for ID: {valgt_id}")
            
            # Valg af banehalvdel baseret på LOCATIONX
            if halvdel == "Modstander":
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50].copy()
            else:
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
                # Spejlvend koordinater for egen halvdel
                df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

            plot_targets = [(c1, "Passes", "pass", "Reds"), (c2, "Duels", "duel", "Blues"), (c3, "Intercepts", "interception", "Greens")]

            for col, title, p_type, cmap in plot_targets:
                with col:
                    st.markdown(f"<p style='text-align:center; font-weight:bold;'>{title}</p>", unsafe_allow_html=True)
                    fig, ax = pitch.draw(figsize=(4, 5))
                    
                    # Find rækker hvor PRIMARYTYPE indeholder vores søgeord
                    mask = df_plot['PRIMARYTYPE'].str.contains(p_type, case=False, na=False)
                    df_filtered = df_plot[mask]
                    
                    if not df_filtered.empty:
                        sns.kdeplot(x=df_filtered['LOCATIONY'], y=df_filtered['LOCATIONX'], 
                                    ax=ax, fill=True, cmap=cmap, alpha=0.7, levels=10, thresh=0.05)
                    else:
                        ax.text(50, 75, "Ingen data", ha='center', va='center', color='gray')
                    st.pyplot(fig, use_container_width=True)
        else:
            st.error("Event-datasæt er tomt eller ikke indlæst korrekt.")

    # --- 4. HØJRE SIDE: KAMP LOG ---
    with main_right:
        st.write("**Seneste kampe**")
        df_f = df_comp[df_comp['TEAM_WYID'] == valgt_id].sort_values('DATE', ascending=False)
        vis_cols = [c for c in ['DATE', 'STATUS', 'GAMEWEEK'] if c in df_f.columns]
        st.dataframe(df_f[vis_cols], use_container_width=True, hide_index=True)
