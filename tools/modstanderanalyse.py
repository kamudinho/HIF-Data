import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch

# Hent turneringsnavne hvis de findes
try:
    from data.season_show import COMP_MAP
except ImportError:
    COMP_MAP = {}

def vis_side(df_team_matches, hold_map, df_events):
    # --- 1. CSS STYLING (Giver luft i toppen) ---
    st.markdown("""
        <style>
            .main-header { font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #333; }
            div[data-testid="stHorizontalBlock"] {
                gap: 1.5rem !important;
                margin-top: 10px !important;
            }
            /* Gør metrics pæne */
            [data-testid="stMetric"] {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                border-left: 5px solid #cc0000;
            }
        </style>
    """, unsafe_allow_html=True)

    if df_team_matches is None or df_team_matches.empty:
        st.error("Kunne ikke finde kampdata i Snowflake.")
        return

    # --- 2. DROPDOWNS (Navigation) ---
    st.markdown('<p class="main-header">Modstanderanalyse</p>', unsafe_allow_html=True)
    
    col_sel1, col_sel2, col_sel3 = st.columns([1.5, 1.5, 1.2])

    with col_sel1:
        aktive_comp_ids = sorted(df_team_matches['COMPETITION_WYID'].unique())
        valgt_comp_id = st.selectbox("Vælg Turnering:", options=aktive_comp_ids,
                                    format_func=lambda x: COMP_MAP.get(int(x), f"Turnering {x}"))

    # Filtrer hold baseret på turnering
    df_comp = df_team_matches[df_team_matches['COMPETITION_WYID'] == valgt_comp_id]
    tilgaengelige_hold_ids = df_comp['TEAM_WYID'].unique()
    
    # Map ID til Navne
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_hold_ids}
    
    with col_sel2:
        valgt_navn = st.selectbox("Vælg Modstander:", options=sorted(navne_dict.keys()))
    
    with col_sel3:
        halvdel = st.radio("Vis hændelser for:", ["Modstander", "Egen"], horizontal=True)

    valgt_id = navne_dict[valgt_navn]

    # --- 3. DATA-FILTERING (Kerne-logikken) ---
    # Vi tjekker om vi har event-data for det specifikke hold
    if df_events is not None and not df_events.empty:
        # Konverter til string for at sikre match (Snowflake vs Pandas typer)
        df_hold_ev = df_events[df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))].copy()
    else:
        df_hold_ev = pd.DataFrame()

    # --- 4. LAYOUT: HEATMAPS ---
    main_left, main_right = st.columns([3, 1])

    with main_left:
        # Skab banen med lidt padding så den ikke rammer toppen
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#ffffff', line_color='#888', 
                              half=True, pad_top=2, pad_bottom=2)
        
        c1, c2, c3 = st.columns(3)
        
        # Definer hvad vi kigger efter i PRIMARYTYPE kolonnen
        plot_configs = [
            (c1, "Afleveringer", "pass", "Reds"),
            (c2, "Dueller", "duel", "Blues"),
            (c3, "Erobringer", "interception", "Greens")
        ]

        if not df_hold_ev.empty:
            # Filtrer på banehalvdel (LOCATIONX i Wyscout: 0-100)
            if halvdel == "Modstander":
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] >= 50].copy()
            else:
                df_plot = df_hold_ev[df_hold_ev['LOCATIONX'] < 50].copy()
                # Spejl koordinaterne så de vises på den øverste halvdel
                df_plot['LOCATIONX'] = 100 - df_plot['LOCATIONX']
                df_plot['LOCATIONY'] = 100 - df_plot['LOCATIONY']

            for col, title, search_term, color_map in plot_configs:
                with col:
                    st.markdown(f"<p style='text-align:center; font-weight:bold;'>{title}</p>", unsafe_allow_html=True)
                    fig, ax = pitch.draw(figsize=(4, 6))
                    
                    # Find de specifikke hændelser
                    df_filtered = df_plot[df_plot['PRIMARYTYPE'].str.contains(search_term, case=False, na=False)]
                    
                    if not df_filtered.empty:
                        sns.kdeplot(x=df_filtered['LOCATIONY'], y=df_filtered['LOCATIONX'], 
                                    ax=ax, fill=True, cmap=color_map, alpha=0.6, levels=10, thresh=0.1)
                    else:
                        ax.text(50, 75, "Ingen data fundet", ha='center', va='center', color='gray', fontsize=10)
                    
                    st.pyplot(fig, use_container_width=True)
        else:
            st.warning(f"⚠️ Ingen hændelsesdata fundet i databasen for {valgt_navn}.")

    # --- 5. HØJRE SIDE: KAMP HISTORIK ---
    with main_right:
        st.markdown(f"### {valgt_navn}")
        df_f = df_comp[df_comp['TEAM_WYID'] == valgt_id].sort_values('DATE', ascending=False)
        
        st.write("**Seneste 5 kampe:**")
        # Viser kun de kolonner vi ved findes: DATE, STATUS, GAMEWEEK
        vis_cols = [c for c in ['DATE', 'STATUS', 'GAMEWEEK'] if c in df_f.columns]
        st.dataframe(df_f[vis_cols].head(5), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.caption("Data leveret af Wyscout via Snowflake AXIS.")
