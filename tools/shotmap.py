import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    df_raw = dp.get('playerstats', pd.DataFrame()) if isinstance(dp, dict) else dp
    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # --- DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)
    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt').astype(str)

    st.subheader("Afslutninger & Chancer")

    tab1, tab2 = st.tabs(["Skudkort", "Chance skabelse (Assists)"])

    # --- TAB 1: SKUDKORT ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        
        with col_ctrl:
            spiller_liste = sorted(df_hif['PLAYER_NAME'].unique().tolist())
            v_spiller_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            
            df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
            if v_spiller_skud != "Hele Holdet":
                df_skud = df_skud[df_skud['PLAYER_NAME'] == v_spiller_skud]
            
            df_skud['ER_MAAL'] = df_skud['TYPE_STR'] == '16'
            
            st.markdown("---")
            st.metric("Skud", len(df_skud))
            st.metric("Mål", int(df_skud['ER_MAAL'].sum()))
            st.metric("xG", f"{df_skud['XG_VAL'].sum():.2f}")

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(10, 12))
            if not df_skud.empty:
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'],
                             s=(df_skud['XG_VAL'] * 1000) + 60,
                             c=df_skud['ER_MAAL'].map({True: HIF_RED, False: 'white'}),
                             edgecolors=HIF_RED, linewidth=1.2, alpha=0.8, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: ASSISTS & KEY PASSES ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        
        with col_ctrl_a:
            v_spiller_a = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_assist")
            
            # Kategorisering af chancer
            df_chance = df_hif[df_hif['TYPE_STR'] == '1'].copy() # Type 1 er pasninger
            
            if v_spiller_a != "Hele Holdet":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_spiller_a]
            
            # Identificer typer via Qualifiers
            mask_assist = df_chance['QUAL_STR'].str.contains('210', na=False)
            mask_2nd = df_chance['QUAL_STR'].str.contains('211', na=False)
            mask_key = df_chance['QUAL_STR'].str.contains('29', na=False)
            
            # Filter dropdown til assist-typer
            type_filter = st.radio("Vis type", ["Alle chancer", "Assists (Mål)", "Key Passes (Skud)", "2nd Assists"])
            
            if type_filter == "Assists (Mål)":
                df_plot_a = df_chance[mask_assist]
            elif type_filter == "Key Passes (Skud)":
                df_plot_a = df_chance[mask_key]
            elif type_filter == "2nd Assists":
                df_plot_a = df_chance[mask_2nd]
            else:
                df_plot_a = df_chance[mask_assist | mask_key | mask_2nd]

            st.markdown("---")
            st.metric("Assists", mask_assist.sum())
            st.metric("Key Passes", mask_key.sum())
            st.metric("2nd Assists", mask_2nd.sum())

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(10, 12))
            
            if not df_plot_a.empty:
                # Farvekodning af pile: Guld for assist, Blå for key pass
                for _, row in df_plot_a.iterrows():
                    color = HIF_GOLD if '210' in row['QUAL_STR'] else HIF_BLUE
                    alpha = 0.9 if '210' in row['QUAL_STR'] else 0.5
                    
                    pitch_a.arrows(row['EVENT_X'], row['EVENT_Y'],
                                   row['PASS_END_X'] if pd.notna(row['PASS_END_X']) else 95, 
                                   row['PASS_END_Y'] if pd.notna(row['PASS_END_Y']) else 50,
                                   color=color, width=2, headwidth=3, headlength=3, ax=ax_a, alpha=alpha)
            
            st.pyplot(fig_a)
            st.caption("Guld: Assists (fører til mål) | Blå: Key Passes (fører til afslutning)")
