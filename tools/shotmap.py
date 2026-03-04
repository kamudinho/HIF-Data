import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # --- DIT LAYOUT OG CSS ---
    st.markdown("""
        <style>
            .stat-box {
                background-color: #f8f9fa;
                padding: 10px 15px;
                border-radius: 8px;
                border-left: 5px solid #df003b;
                margin-bottom: 8px;
            }
            .stat-label {
                font-size: 0.8rem;
                text-transform: uppercase;
                color: #666;
                font-weight: bold;
                display: flex;
                align-items: center;
            }
            .stat-value {
                font-size: 1.6rem;
                font-weight: 800;
                color: #1a1a1a;
                margin-left: 22px;
                line-height: 1.1;
            }
            .dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        </style>
    """, unsafe_allow_html=True)
    
    # Hent data sikkert
    df_raw = dp.get('playerstats', pd.DataFrame())
    if df_raw.empty:
        df_raw = dp.get('opta_shotevents', pd.DataFrame())
        
    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # Data rens og forberedelse
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Sikr at typerne er korrekte for at undgå Series-fejl
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip()
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
            
            # RETTELSE: Brug .item() eller int() på selve sum-resultatet
            n_maal = int((df_skud['TYPE_STR'] == '16').sum())
            n_skud = len(df_skud)

            st.markdown(f"""
                <div class="stat-box" style="margin-top: 10px;">
                    <div class="stat-label"><span class="dot" style="background-color:white; border:2px solid {HIF_RED}"></span> Afslutninger</div>
                    <div class="stat-value">{n_skud}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:{HIF_RED}"></span> Mål</div>
                    <div class="stat-value">{n_maal}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(7, 9))
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
            
            # Find chancer (210=Assist, 29=Key Pass, 211=2nd Assist)
            is_chance = df_hif['QUAL_STR'].str.contains('210|29|211', na=False)
            df_chance = df_hif[(df_hif['TYPE_STR'] == '1') & is_chance].copy()
            
            if v_a != "Hvidovre IF":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_a]
            
            # RETTELSE: Vi konverterer resultatet af summen direkte til int
            val_assist = int(df_chance['QUAL_STR'].str.contains('210').sum())
            # Key Pass er ID 29, men ikke hvis det også er en Assist (210)
            val_key = int((df_chance['QUAL_STR'].str.contains('29')) & (~df_chance['QUAL_STR'].str.contains('210'))).sum()
            val_2nd = int(df_chance['QUAL_STR'].str.contains('211').sum())

            st.markdown(f"""
                <div class="stat-box" style="margin-top: 10px;">
                    <div class="stat-label"><span class="dot" style="background-color:{HIF_GOLD}"></span> Assists</div>
                    <div class="stat-value">{val_assist}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:#999999"></span> Key Passes</div>
                    <div class="stat-value">{val_key}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:{HIF_BLUE}"></span> 2nd Assists</div>
                    <div class="stat-value">{val_2nd}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7, 9))
            
            if not df_chance.empty:
                # Arrows
                pitch_a.arrows(df_chance['EVENT_X'].astype(float), df_chance['EVENT_Y'].astype(float),
                               df_chance['PASS_END_X'].astype(float), df_chance['PASS_END_Y'].astype(float),
                               color='#dddddd', width=2, ax=ax_a, zorder=1)
                
                # Farvelogik til prikker
                def color_map(q):
                    if '210' in q: return HIF_GOLD
                    if '211' in q: return HIF_BLUE
                    return '#999999'
                
                df_chance['DOT_COLOR'] = df_chance['QUAL_STR'].apply(color_map)
                pitch_a.scatter(df_chance['EVENT_X'], df_chance['EVENT_Y'], 
                                s=110, color=df_chance['DOT_COLOR'], edgecolors='white', 
                                linewidth=1.2, ax=ax_a, zorder=2)
            st.pyplot(fig_a, use_container_width=True)
