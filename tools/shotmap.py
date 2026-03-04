import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # 1. Hent data
    df_raw = dp.get('opta_shotevents', pd.DataFrame())
    if df_raw.empty:
        df_raw = dp.get('playerstats', pd.DataFrame())

    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # 2. Forberedelse af data (Gør alt klart til filtrering)
    df_raw.columns = [c.upper() for c in df_raw.columns]
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Sikr os at vi har strenge at lede i
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False)
    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt')

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        with col_ctrl:
            spiller_liste = sorted(df_hif['PLAYER_NAME'].unique().tolist())
            v_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            
            df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
            if v_skud != "Hele Holdet":
                df_skud = df_skud[df_skud['PLAYER_NAME'] == v_skud]
            
            # Sikker optælling
            n_maal = int((df_skud['TYPE_STR'] == '16').sum())
            n_skud = len(df_skud)

            st.markdown(f"""
                <div class="stat-box" style="margin-top: 10px;">
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
            fig, ax = pitch.draw(figsize=(7.5, 9.5))
            if not df_skud.empty:
                c_map = (df_skud['TYPE_STR'] == '16').map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'], s=100, 
                             c=c_map, edgecolors=HIF_RED, linewidth=1.2, ax=ax)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 2: ASSISTS ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        with col_ctrl_a:
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_assist")
            
            # VI BRUGER DIN LISTAGG (QUAL_STR) HER - DET VIRKER ALTID
            # 210 = Assist, 29 = Key Pass, 211 = 2nd Assist
            is_assist = df_hif['QUAL_STR'].str.contains('210', na=False)
            is_key = df_hif['QUAL_STR'].str.contains('29', na=False)
            is_2nd = df_hif['QUAL_STR'].str.contains('211', na=False)
            
            df_chance = df_hif[(df_hif['TYPE_STR'] == '1') & (is_assist | is_key | is_2nd)].copy()
            
            if v_a != "Hvidovre IF":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_a]
            
            # Beregn værdier til boksene
            val_assist = int(df_chance['QUAL_STR'].str.contains('210').sum())
            val_key = int((df_chance['QUAL_STR'].str.contains('29')) & (~df_chance['QUAL_STR'].str.contains('210'))).sum()
            val_2nd = int(df_chance['QUAL_STR'].str.contains('211').sum())

            st.markdown(f"""
                <div class="stat-box" style="margin-top: 10px;">
                    <div class="stat-label">Assists</div>
                    <div class="stat-value">{val_assist}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">Key Passes</div>
                    <div class="stat-value">{val_key}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">2nd Assists</div>
                    <div class="stat-value">{val_2nd}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7.5, 9.5))
            
            if not df_chance.empty:
                # Arrows (konverteret til float for en sikkerheds skyld)
                pitch_a.arrows(df_chance['EVENT_X'].astype(float), df_chance['EVENT_Y'].astype(float),
                               df_chance['PASS_END_X'].astype(float), df_chance['PASS_END_Y'].astype(float),
                               color='#eeeeee', width=2, ax=ax_a, zorder=1)
                
                # Farv prikkerne
                def color_logic(q):
                    if '210' in q: return HIF_GOLD
                    if '211' in q: return HIF_BLUE
                    return '#999999'
                
                df_chance['DOT_COLOR'] = df_chance['QUAL_STR'].apply(color_logic)
                pitch_a.scatter(df_chance['EVENT_X'], df_chance['EVENT_Y'], 
                                s=110, color=df_chance['DOT_COLOR'], edgecolors='white', ax=ax_a, zorder=2)
            st.pyplot(fig_a, use_container_width=True)
