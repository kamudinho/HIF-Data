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
                gap: 0.5rem !important;
                margin-top: -30px !important;
            }
            .stMetric { 
                background-color: #ffffff; padding: 10px; border-radius: 8px; 
                border-bottom: 3px solid #df003b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
            }
            [data-testid="stMetricValue"] { font-size: 18px !important; }
        </style>
    """, unsafe_allow_html=True)

    if df_team_matches is None or df_team_matches.empty:
        st.error("Kunne ikke finde kampdata.")
        return

    # --- 2. DROPDOWN MENUER ---
    aktive_comp_ids = sorted(df_team_matches['COMPETITION_WYID'].unique()) if 'COMPETITION_WYID' in df_team_matches.columns else []

    col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])

    with col_sel1:
        valgt_comp_id = st.selectbox("Turnering:", options=aktive_comp_ids,
                                    format_func=lambda x: COMP_MAP.get(int(x), f"Turnering {x}"))

    # Filtrering baseret på dine faktiske kolonner: TEAM_WYID og COMPETITION_WYID
    df_comp = df_team_matches[df_team_matches['COMPETITION_WYID'] == valgt_comp_id]
    tilgaengelige_hold_ids = df_comp['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_hold_ids}
    
    with col_sel2:
        valgt_navn = st.selectbox("Modstander:", options=sorted(navne_dict.keys()))
    
    with col_sel3:
        halvdel = st.radio("Halvdel:", ["Modstander", "Egen"], horizontal=True)

    valgt_id = navne_dict[valgt_navn]
    
    # --- 3. EVENT ANALYSE (Heatmaps) ---
    main_left, main_right = st.columns([2.5, 1])

    with main_left:
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#f8f9fa', line_color='#333', 
                              half=True, pad_top=0, pad_bottom=0, pad_left=0, pad_right=0)
        
        c1, c2, c3 = st.columns(3)

        if df_events is not None and not df_events.empty:
            # Vi bruger dine præcise kolonnenavne: TEAM_WYID, LOCATIONX, LOCATIONY, PRIMARYTYPE
            df_hold_ev = df_events[df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))].copy()

            if halvdel == "Modstander":
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50].copy()
            else:
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
                df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

            for col, title, p_type, cmap in [(c1, "Passes", "pass", "Reds"), (c2, "Duels", "duel", "Blues"), (c3, "Intercepts", "interception", "Greens")]:
                with col:
                    st.markdown(f"<p style='text-align:center; font-weight:bold; margin-bottom:-5px;'>{title}</p>", unsafe_allow_html=True)
                    fig, ax = pitch.draw(figsize=(4, 5))
                    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
                    
                    mask = df_hold_ev['PRIMARYTYPE'].str.contains(p_type, case=False, na=False)
                    df_filtered = df_plot[df_plot['PRIMARYTYPE'].str.contains(p_type, case=False, na=False)] if not df_plot.empty else pd.DataFrame()
                    
                    if not df_filtered.empty:
                        sns.kdeplot(x=df_filtered['LOCATIONY'], y=df_filtered['LOCATIONX'], ax=ax, fill=True, cmap=cmap, alpha=0.6, levels=8, thresh=0.1)
                    else:
                        ax.text(50, 75, "Ingen data", ha='center', va='center', color='gray', fontsize=8)
                    st.pyplot(fig, use_container_width=True)

    # --- 4. HØJRE SIDE: KAMP LOG (Data vi rent faktisk har) ---
    with main_right:
        st.subheader(valgt_navn)
        
        # Da vi ikke har GOALS/XG i TEAMMATCHES, viser vi kamp-historikken i stedet
        df_f = df_comp[df_comp['TEAM_WYID'] == valgt_id].sort_values('DATE', ascending=False)
        
        st.info("Statistik (xG/Mål) kræver kobling til Advanced Stats tabellen.")
        
        with st.expander("Seneste kampe", expanded=True):
            # Vi bruger kun kolonner fra din liste: DATE, STATUS, GAMEWEEK
            vis_cols = ['DATE', 'STATUS', 'GAMEWEEK']
            st.dataframe(df_f[vis_cols], use_container_width=True, hide_index=True)
