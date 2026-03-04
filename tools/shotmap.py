import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Konstanter
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'
HIF_BLUE = '#0056a3'
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # --- CSS OG LAYOUT (Uændret) ---
    st.markdown("""<style>...</style>""", unsafe_allow_html=True) # Din eksisterende CSS

    df_raw = dp.get('playerstats', pd.DataFrame())
    if df_raw.empty:
        df_raw = dp.get('opta_shotevents', pd.DataFrame())
    
    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # --- DATA RENS (Her sikrer vi tallene) ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Konverter koordinater til tal med det samme for at undgå fejl i plotting
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_END_X', 'PASS_END_Y']:
        if col in df_hif.columns:
            df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce')

    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip()
    
    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        with col_ctrl:
            spiller_liste = sorted(df_hif['PLAYER_NAME'].dropna().unique().tolist())
            v_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            
            df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
            if v_skud != "Hele Holdet":
                df_skud = df_skud[df_skud['PLAYER_NAME'] == v_skud]
            
            # SIKKER TÆLLING
            n_maal = int((df_skud['TYPE_STR'] == '16').sum())
            n_skud = len(df_skud)

            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label">Afslutninger</div>
                    <div class="stat-value">{n_skud}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Mål</div>
                    <div class="stat-value">{n_maal}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(7, 9))
            if not df_skud.empty:
                c_map = (df_skud['TYPE_STR'] == '16').map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'], s=150, 
                             c=c_map, edgecolors=HIF_RED, linewidth=1.5, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: ASSISTS ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        with col_ctrl_a:
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_assist")
            
            # Filtrer chancer
            is_chance = df_hif['QUAL_STR'].str.contains('210|29|211', na=False)
            df_chance = df_hif[(df_hif['TYPE_STR'] == '1') & is_chance].copy()
            
            if v_a != "Hvidovre IF":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_a]
            
            # SIKKER TÆLLING (FIX: sum() inde i int())
            val_assist = int(df_chance['QUAL_STR'].str.contains('210', na=False).sum())
            val_key = int((df_chance['QUAL_STR'].str.contains('29', na=False) & ~df_chance['QUAL_STR'].str.contains('210', na=False)).sum())
            val_2nd = int(df_chance['QUAL_STR'].str.contains('211', na=False).sum())

            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label">Assists</div><div class="stat-value">{val_assist}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Key Passes</div><div class="stat-value">{val_key}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7, 9))
            if not df_chance.empty:
                # Tegn pile
                pitch_a.arrows(df_chance.EVENT_X, df_chance.EVENT_Y,
                             df_chance.PASS_END_X, df_chance.PASS_END_Y,
                             color='#dddddd', width=2, ax=ax_a)
                
                # Farvelæg punkter
                def get_color(row):
                    if '210' in row['QUAL_STR']: return HIF_GOLD
                    if '211' in row['QUAL_STR']: return HIF_BLUE
                    return '#999999'
                
                df_chance['color'] = df_chance.apply(get_color, axis=1)
                pitch_a.scatter(df_chance.EVENT_X, df_chance.EVENT_Y, s=120, 
                               color=df_chance.color, edgecolors='white', ax=ax_a)
            st.pyplot(fig_a)
