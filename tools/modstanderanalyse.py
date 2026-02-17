import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from mplsoccer import VerticalPitch
import numpy as np

def vis_side(df_team_matches, hold_map, df_events):
    # --- 1. CSS STYLING (HIF Look) ---
    st.markdown("""
        <style>
        .stMetric { 
            background-color: #ffffff; 
            padding: 10px; 
            border-radius: 8px; 
            border-bottom: 3px solid #df003b; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
            margin-bottom: 10px;
        }
        [data-testid="stMetricValue"] { font-size: 20px !important; font-weight: bold; }
        [data-testid="stMetricLabel"] { font-size: 14px !important; color: #555; }
        </style>
    """, unsafe_allow_html=True)

    if df_team_matches is None or df_team_matches.empty:
        st.error("Kunne ikke finde kampdata.")
        return

    # --- 2. VALG AF MODSTANDER ---
    tilgaengelige_ids = df_team_matches['TEAM_WYID'].unique()
    navne_dict = {hold_map.get(str(int(tid)), f"Ukendt ({tid})"): tid for tid in tilgaengelige_ids}
    
    valgt_navn = st.selectbox("Vælg modstander:", options=sorted(navne_dict.keys()))
    valgt_id = navne_dict[valgt_navn]
    
    # Forbered data
    df_f = df_team_matches[df_team_matches['TEAM_WYID'] == valgt_id].copy()
    df_f['DATE'] = pd.to_datetime(df_f['DATE']).dt.date
    
    # --- 3. HOVEDLAYOUT ---
    # Venstre side: De 3 heatmaps | Højre side: Alle de statistiske bokse
    main_left, main_right = st.columns([2, 1])

    with main_left:
        st.subheader(f"Positionsanalyse: {valgt_navn}")
        pitch = VerticalPitch(pitch_type='wyscout', pitch_color='#f8f9fa', line_color='#1a1a1a', linewidth=1)
        
        c1, c2, c3 = st.columns(3)

        if df_events is not None and not df_events.empty:
            df_events.columns = [c.upper() for c in df_events.columns]
            df_hold = df_events[df_events['TEAM_WYID'].astype(str) == str(int(valgt_id))].copy()

            # Heatmap farver: Rød (Pass), Blå (Duel), Grøn (Interception)
            configs = [
                (c1, "Afleveringer", "pass", "Reds"),
                (c2, "Dueller", "duel", "Blues"),
                (c3, "Interceptions", "interception", "Greens")
            ]

            for col, title, p_type, cmap in configs:
                with col:
                    st.caption(title)
                    fig, ax = pitch.draw(figsize=(4, 6))
                    mask = df_hold['PRIMARYTYPE'].str.contains(p_type, case=False, na=False)
                    df_filtered = df_hold[mask]
                    if not df_filtered.empty:
                        sns.kdeplot(x=df_filtered['LOCATIONY'], y=df_filtered['LOCATIONX'], 
                                    ax=ax, fill=True, cmap=cmap, alpha=0.6, 
                                    clip=((0, 100), (0, 100)), levels=10)
                    st.pyplot(fig)

    # --- 4. HØJRE SIDE: STATISTISKE BOKSE (Metrics) ---
    with main_right:
        st.subheader("Holdets Profil")
        
        # Vi deler metrics op i kategorier (3 rækker af 2 kolonner)
        
        # Række 1: Offensivt
        st.write("**Offensiv**")
        col_off1, col_off2 = st.columns(2)
        col_off1.metric("Gns. xG", round(df_f['XG'].mean(), 2))
        col_off2.metric("Skud/Kamp", round(df_f['SHOTS'].mean(), 1))

        # Række 2: Spilstyring
        st.write("**Spilstyring**")
        col_ctrl1, col_ctrl2 = st.columns(2)
        col_ctrl1.metric("Possession", f"{round(df_f['POSSESSIONPERCENT'].mean(), 0)}%")
        col_ctrl2.metric("Gns. Mål", round(df_f['GOALS'].mean(), 1))

        # Række 3: Disciplin / Defensivt
        st.write("**Defensiv & Disciplin**")
        col_def1, col_def2 = st.columns(2)
        # Tjekker om kolonnerne findes før beregning
        y_cards = df_f['YELLOWCARDS'].mean() if 'YELLOWCARDS' in df_f else 0
        r_cards = df_f['REDCARDS'].sum() if 'REDCARDS' in df_f else 0
        
        col_def1.metric("Gule kort/K", round(y_cards, 1))
        col_def2.metric("Røde kort (Total)", int(r_cards))

        st.markdown("---")
        
        # Konverteringsrate Progress Bar
        total_shots = df_f['SHOTS'].sum()
        total_goals = df_f['GOALS'].sum()
        if total_shots > 0:
            rate = (total_goals / total_shots) * 100
            st.write(f"**Effektivitet (Mål/Skud):** {round(rate, 1)}%")
            st.progress(min(rate/30, 1.0))

        st.info(f"""
        **Kort analyse:**
        Holdet har en gennemsnitlig xG på {round(df_f['XG'].mean(), 2)}. 
        De tre heatmaps viser deres taktiske tyngdepunkter i opbygning (Rød), defensive dueller (Blå) og opspils-brydninger (Grøn).
        """)

    # --- 5. RÅ DATA TABEL ---
    with st.expander("Se alle kampdata"):
        st.dataframe(df_f.sort_values('DATE', ascending=False), use_container_width=True)
