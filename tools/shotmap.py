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

    tab1, tab2 = st.tabs(["Skudkort", "Assists & Key Passes"])

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
            st.metric("xG Total", f"{df_skud['XG_VAL'].sum():.2f}")

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(8, 10))
            if not df_skud.empty:
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'],
                             s=(df_skud['XG_VAL'] * 1000) + 60,
                             c=df_skud['ER_MAAL'].map({True: HIF_RED, False: 'white'}),
                             edgecolors=HIF_RED, linewidth=1.2, alpha=0.8, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: ASSISTS (Med prikker og pile) ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        
        with col_ctrl_a:
            v_spiller_a = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_assist")
            
            # Find alle relevante chancer (Assists=210, KeyPass=29, 2nd=211)
            mask_chance = (df_hif['QUAL_STR'].str.contains('210|29|211', na=False)) & (df_hif['TYPE_STR'] == '1')
            df_chance = df_hif[mask_chance].copy()
            
            if v_spiller_a != "Hele Holdet":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_spiller_a]
            
            st.markdown("---")
            # Stats baseret på qualifiers
            n_assist = df_chance['QUAL_STR'].str.contains('210').sum()
            n_key = df_chance['QUAL_STR'].str.contains('29').sum()
            n_2nd = df_chance['QUAL_STR'].str.contains('211').sum()
            
            st.metric("Assists (Mål)", n_assist)
            st.metric("Key Passes (Skud)", n_key)
            st.metric("2nd Assists", n_2nd)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
            
            if not df_chance.empty:
                # 1. Tegn Pile
                pitch_a.arrows(df_chance['EVENT_X'], df_chance['EVENT_Y'],
                               df_chance['PASS_END_X'].fillna(95), df_chance['PASS_END_Y'].fillna(50),
                               color='#dddddd', width=2, headwidth=3, headlength=3, ax=ax_a, zorder=1)
                
                # 2. Tegn Prikker (Startpunktet) - Farvekodet efter type
                # Vi laver en hjælpekolonne til farven
                def get_color(q):
                    if '210' in q: return HIF_GOLD # Assist
                    if '211' in q: return HIF_BLUE # 2nd Assist
                    return '#999999' # Key Pass
                
                df_chance['COLOR'] = df_chance['QUAL_STR'].apply(get_color)
                
                pitch_a.scatter(df_chance['EVENT_X'], df_chance['EVENT_Y'], 
                                s=120, color=df_chance['COLOR'], edgecolors='white', 
                                linewidth=1, ax=ax_a, zorder=2)
            
            st.pyplot(fig_a)
            st.markdown(f"<span style='color:{HIF_GOLD}'>●</span> Assist | <span style='color:#999999'>●</span> Key Pass | <span style='color:{HIF_BLUE}'>●</span> 2nd Assist", unsafe_allow_html=True)
