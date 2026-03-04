import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp, logo_map=None):
    # --- VI BEHOLDER DIT LAYOUT PRÆCIS SOM DET VAR ---
    st.markdown("""
        <style>
            .block-container { padding-top: 0.5rem !important; }
            .stTabs [data-baseweb="tab-panel"] { 
                margin-top: -15px !important; 
                padding-top: 0px !important; 
            }
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

    # Data hentning - tjekker begge mulige nøgler
    df_raw = dp.get('opta_shotevents', pd.DataFrame())
    if df_raw.empty:
        df_raw = dp.get('playerstats', pd.DataFrame())

    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # Sørg for kolonnenavne er store pga. Snowflake
    df_raw.columns = [c.upper() for c in df_raw.columns]
    
    # Filtrér på HIF
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    
    # Præ-konvertér typer for at undgå konverteringsfejl senere
    df_hif['EVENT_TYPEID'] = pd.to_numeric(df_hif['EVENT_TYPEID'], errors='coerce').fillna(0).astype(int)
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str)
    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt').astype(str)

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        with col_ctrl:
            spiller_liste = sorted(df_hif['PLAYER_NAME'].unique().tolist())
            v_spiller_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            
            df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
            if v_spiller_skud != "Hele Holdet":
                df_skud = df_skud[df_skud['PLAYER_NAME'] == v_spiller_skud]
            
            # RETTELSE: Brug .sum() på en boolean maske og konvertér til int sikkert
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
            fig, ax = pitch.draw(figsize=(7.5, 9.5))
            if not df_skud.empty:
                # Farv prikkerne: Rød hvis mål (16), hvid hvis ikke
                c_map = (df_skud['TYPE_STR'] == '16').map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'],
                             s=100, c=c_map, edgecolors=HIF_RED, linewidth=1.2, alpha=0.9, ax=ax)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 2: ASSISTS ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        with col_ctrl_a:
            v_spiller_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_assist")
            
            # Sikr at flag-kolonnerne findes som tal
            for col in ['IS_ASSIST', 'IS_KEY_PASS', 'IS_2ND_ASSIST']:
                if col not in df_hif.columns:
                    df_hif[col] = 0
                df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0).astype(int)

            mask_chance = (df_hif['EVENT_TYPEID'] == 1) & (
                (df_hif['IS_ASSIST'] == 1) | 
                (df_hif['IS_KEY_PASS'] == 1) | 
                (df_hif['IS_2ND_ASSIST'] == 1)
            )
            df_chance = df_hif[mask_chance].copy()
            
            if v_spiller_a != "Hvidovre IF":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_spiller_a]
            
            # RETTELSE: Sikker optælling af de enkelte kategorier
            n_assist = int(df_chance['IS_ASSIST'].sum())
            n_key = int((df_chance['IS_KEY_PASS'] == 1) & (df_chance['IS_ASSIST'] == 0)).sum()
            n_2nd = int(df_chance['IS_2ND_ASSIST'].sum())

            st.markdown(f"""
                <div class="stat-box" style="margin-top: 10px;">
                    <div class="stat-label"><span class="dot" style="background-color:{HIF_GOLD}"></span> Assists</div>
                    <div class="stat-value">{n_assist}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:#999999"></span> Key Passes</div>
                    <div class="stat-value">{n_key}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:{HIF_BLUE}"></span> 2nd Assists</div>
                    <div class="stat-value">{n_2nd}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7.5, 9.5))
            
            if not df_chance.empty:
                # Tegn pile (konvertér koordinater til float for at undgå fejl)
                pitch_a.arrows(df_chance['EVENT_X'].astype(float), df_chance['EVENT_Y'].astype(float),
                               df_chance['PASS_END_X'].astype(float), df_chance['PASS_END_Y'].astype(float),
                               color='#eeeeee', width=2, headwidth=3, headlength=3, ax=ax_a, zorder=1)
                
                # Farvekode prikkerne
                def get_color(row):
                    if row['IS_ASSIST'] == 1: return HIF_GOLD
                    if row['IS_2ND_ASSIST'] == 1: return HIF_BLUE
                    return '#999999'
                
                df_chance['COLOR'] = df_chance.apply(get_color, axis=1)
                pitch_a.scatter(df_chance['EVENT_X'], df_chance['EVENT_Y'], 
                                s=110, color=df_chance['COLOR'], edgecolors='white', 
                                linewidth=1.2, ax=ax_a, zorder=2)
            st.pyplot(fig_a, use_container_width=True)
