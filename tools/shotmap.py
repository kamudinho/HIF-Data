import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
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
    
    df_raw = dp.get('opta_shotevents', pd.DataFrame()) if isinstance(dp, dict) else dp
    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # --- DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # TVUNGEN KONVERTERING: Gør tekst-koordinater til tal med det samme
    for col in ['EVENT_X', 'EVENT_Y', 'PASS_START_X', 'PASS_START_Y']:
        if col in df_hif.columns:
            df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)

    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)
    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt').astype(str)

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    # --- TAB 1: SKUDKORT ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        with col_ctrl:
            spiller_liste = sorted(df_hif['PLAYER_NAME'].unique().tolist())
            v_spiller_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
            if v_spiller_skud != "Hele Holdet":
                df_skud = df_skud[df_skud['PLAYER_NAME'] == v_spiller_skud]
            
            df_skud['ER_MAAL'] = df_skud['EVENT_OUTCOME'].astype(str) == '1'
            n_maal = int(df_skud['ER_MAAL'].sum())
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
            fig, ax = pitch.draw(figsize=(7.5, 9.5))
            if not df_skud.empty:
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'],
                             s=150, c=df_skud['ER_MAAL'].map({True: HIF_RED, False: 'white'}),
                             edgecolors=HIF_RED, linewidth=1.2, alpha=0.9, ax=ax)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 2: ASSISTS ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        with col_ctrl_a:
            v_spiller_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_assist")
            
            # Vi finder alle assisterede skud
            df_chance = df_hif[df_hif['QUAL_STR'].str.contains('210|29', na=False)].copy()
            
            # Korrekt tælling: 210 er Assist, resten er Key Passes (Shot Assists)
            n_assist = df_chance['QUAL_STR'].str.contains('210').sum()
            n_key = len(df_chance) - n_assist 

            st.markdown(f"""
                <div class="stat-box" style="margin-top: 10px;">
                    <div class="stat-label"><span class="dot" style="background-color:{HIF_GOLD}"></span> Assists</div>
                    <div class="stat-value">{n_assist}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:#999999"></span> Shot Assists</div>
                    <div class="stat-value">{n_key}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7.5, 9.5))
            
            # Vi tegner kun hvis vi har start-koordinater
            df_plot = df_chance[df_chance['PASS_START_X'] > 0].copy()
            
            if not df_plot.empty:
                # 1. Tegn pilene (zorder 1 - nederst)
                pitch_a.arrows(df_plot['PASS_START_X'], df_plot['PASS_START_Y'],
                               df_plot['EVENT_X'], df_plot['EVENT_Y'],
                               color='#dddddd', width=2, headwidth=3, headlength=3, ax=ax_a, zorder=1)
                
                # 2. Tegn Shot Assists (zorder 2)
                df_s = df_plot[~df_plot['QUAL_STR'].str.contains('210')]
                pitch_a.scatter(df_s['EVENT_X'], df_s['EVENT_Y'], 
                                s=100, color='#999999', edgecolors='white', 
                                linewidth=1, alpha=0.6, ax=ax_a, zorder=2)
                
                # 3. Tegn Assists (zorder 3 - øverst)
                df_a = df_plot[df_plot['QUAL_STR'].str.contains('210')]
                pitch_a.scatter(df_a['EVENT_X'], df_a['EVENT_Y'], 
                                s=150, color=HIF_GOLD, edgecolors='white', 
                                linewidth=1.5, ax=ax_a, zorder=3)
            
            st.pyplot(fig_a, use_container_width=True)
