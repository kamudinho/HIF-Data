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
    # --- 1. CSS STYLING ---
    st.markdown("""
        <style>
            div[data-testid="stHorizontalBlock"] {
                gap: 1rem !important;
                margin-top: 0px !important; 
            }
            .stMetric { 
                background-color: #ffffff; padding: 15px; border-radius: 10px; 
                border-bottom: 4px solid #cc0000; box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            }
            [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: bold !important; color: #333; }
            [data-testid="stMetricLabel"] { font-size: 14px !important; text-transform: uppercase; letter-spacing: 1px; }
        </style>
    """, unsafe_allow_html=True)

    if df_team_matches is None or df_team_matches.empty:
        st.error("Kunne ikke finde kampdata.")
        return

    # --- 2. FILTRERING & DROPDOWNS ---
    aktive_comp_ids = sorted(df_team_matches['COMPETITION_WYID'].unique())
    
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
    
    # Filtrer statistikken for det valgte hold
    df_hold_stats = df_comp[df_comp['TEAM_WYID'] == valgt_id].copy()

    # --- 3. METRIC BOXES (Gennemsnit for sæsonen) ---
    st.markdown(f"### Statistisk overblik: {valgt_navn}")
    m1, m2, m3, m4 = st.columns(4)
    
    # Hjælpefunktion til at hente stats sikkert
    def get_avg(col_name, decimals=1):
        if col_name in df_hold_stats.columns:
            return round(df_hold_stats[col_name].mean(), decimals)
        return 0.0

    with m1:
        st.metric("Gns. Mål", get_avg('GOALS'))
    with m2:
        st.metric("Gns. xG", get_avg('XG', 2))
    with m3:
        st.metric("Skud pr. kamp", get_avg('SHOTS'))
    with m4:
        pos = get_avg('POSSESSIONPERCENT', 0)
        st.metric("Possession", f"{int(pos)}%" if pos > 0 else "N/A")

    st.markdown("---")

    # --- 4. HEATMAPS & KAMP LOG ---
    main_left, main_right = st.columns([2.8, 1])

    with main_left:
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#f8f9fa', line_color='#333', 
                              half=True, pad_top=0.5, pad_bottom=0.5)
        
        c1, c2, c3 = st.columns(3)

        if df_events is not None and not df_events.empty:
            # Matcher holdets events
            df_hold_ev = df_events[df_events['TEAM_WYID'].astype(str).str.contains(str(int(valgt_id)))].copy()
            
            if not df_hold_ev.empty:
                if halvdel == "Modstander":
                    df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50].copy()
                else:
                    df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
                    df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                    df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

                # Heatmap generation
                targets = [(c1, "Afleveringer", "pass", "Reds"), 
                           (c2, "Dueller", "duel", "Blues"), 
                           (c3, "Erobringer", "interception", "Greens")]

                for col, title, p_type, cmap in targets:
                    with col:
                        st.markdown(f"<p style='text-align:center; font-weight:bold;'>{title}</p>", unsafe_allow_html=True)
                        fig, ax = pitch.draw(figsize=(4, 5))
                        mask = df_plot['PRIMARYTYPE'].str.contains(p_type, case=False, na=False)
                        df_filtered = df_plot[mask]
                        
                        if not df_filtered.empty:
                            sns.kdeplot(x=df_filtered['LOCATIONY'], y=df_filtered['LOCATIONX'], 
                                        ax=ax, fill=True, cmap=cmap, alpha=0.7, levels=10, thresh=0.05)
                        else:
                            ax.text(50, 75, "Ingen data", ha='center', va='center', color='gray')
                        st.pyplot(fig, use_container_width=True)
            else:
                st.warning("Ingen hændelsesdata fundet for dette hold.")

    with main_right:
        st.write("**Seneste kampe**")
        # Viser dato og status (W/D/L hvis det findes)
        df_log = df_hold_stats.sort_values('DATE', ascending=False)
        cols_to_show = [c for c in ['DATE', 'STATUS', 'GAMEWEEK'] if c in df_log.columns]
        st.dataframe(df_log[cols_to_show], use_container_width=True, hide_index=True)
