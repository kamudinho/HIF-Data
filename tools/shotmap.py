import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# --- KONFIGURATION ---
HIF_RED = '#df003b' 
HIF_BLUE = '#0055aa'
HIF_GOLD = '#ffd700'
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp=None):
    st.markdown(f"""
        <div style="background-color:{HIF_RED}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">HVIDOVRE IF - OFFENSIV ANALYSE</h3>
        </div>
    """, unsafe_allow_html=True)
    
    df_raw = dp.get('playerstats', pd.DataFrame())
    if df_raw.empty:
        st.info("Ingen data fundet.")
        return

    # --- 1. DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Vi sikrer os at vi kan søge i qualifiers og typer uanset format
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip().str.upper()
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)

    # --- 2. GLOBAL SPILLER DROPDOWN (ØVERST) ---
    spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
    valgt_spiller = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste)
    
    # --- 3. TABS ---
    tab1, tab2 = st.tabs(["Skudkort", "Assists"])

    # --- TAB 1: SKUDKORT ---
    with tab1:
        skud_typer = ['13', '14', '15', '16', 'G', 'PG', '38']
        df_skud = df_hif[df_hif['TYPE_STR'].isin(skud_typer)].copy()
        
        if valgt_spiller != "Hele Holdet":
            df_skud = df_skud[df_skud['PLAYER_NAME'] == valgt_spiller]

        df_skud['ER_MAAL'] = df_skud['TYPE_STR'].isin(['16', 'G', 'PG'])

        col_map, col_stats = st.columns([2.2, 1])
        with col_map:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#444444')
            fig, ax = pitch.draw(figsize=(8, 10))
            for _, row in df_skud.iterrows():
                color = HIF_RED if row['ER_MAAL'] else HIF_BLUE
                size = (float(row.get('XG_VAL', 0.1)) * 1500) + 100
                pitch.scatter(row['EVENT_X'], row['EVENT_Y'], s=size, c=color, 
                              marker='o', edgecolors='white', ax=ax, alpha=0.7, zorder=3)
            st.pyplot(fig)
        with col_stats:
            st.metric("Skud", len(df_skud))
            st.metric("Mål", int(df_skud['ER_MAAL'].sum()))

    # --- TAB 2: ASSISTS ---
    with tab2:
        # Bredere søgning:
        # 1. Type er 'AS' (Assist)
        # 2. Qualifier indeholder '210' (Assist)
        # 3. Qualifier indeholder '154' (Intentional Assist)
        # 4. Qualifier indeholder '29' (Assisted)
        assist_filter = (
            (df_hif['TYPE_STR'] == 'AS') | 
            (df_hif['QUAL_STR'].str.contains('210', na=False)) |
            (df_hif['QUAL_STR'].str.contains('154', na=False)) |
            (df_hif['QUAL_STR'].str.contains('29', na=False))
        )
        
        df_assists = df_hif[assist_filter].copy().drop_duplicates(subset=['EVENT_ID'])

        if valgt_spiller != "Hele Holdet":
            df_assists = df_assists[df_assists['PLAYER_NAME'] == valgt_spiller]

        col_map_a, col_stats_a = st.columns([2.2, 1])
        with col_map_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', line_color='#444444')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
            
            if not df_assists.empty:
                for _, row in df_assists.iterrows():
                    # Vi bruger EVENT_X/Y som start og forsøger at gætte slutpunktet i feltet hvis data mangler
                    ex = row.get('PASS_END_X', 90) 
                    ey = row.get('PASS_END_Y', 50)
                    
                    pitch_a.arrows(row['EVENT_X'], row['EVENT_Y'], ex, ey, 
                                   color=HIF_GOLD, width=2, headwidth=4, ax=ax_a, zorder=2)
                    pitch_a.scatter(row['EVENT_X'], row['EVENT_Y'], color=HIF_GOLD, 
                                    marker='o', edgecolors='white', s=150, ax=ax_a, zorder=3)
            else:
                st.warning("Ingen assist-data fundet med de nuværende filtre.")
                
            st.pyplot(fig_a)

        with col_stats_a:
            st.metric("Assists", len(df_assists))
            if not df_assists.empty:
                st.write("Detaljer:")
                st.dataframe(df_assists[['PLAYER_NAME', 'TYPE_STR', 'EVENT_ID']])
