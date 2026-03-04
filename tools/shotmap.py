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

    # Data hentning - tjekker begge mulige nøgler for at være sikker
    df_raw = dp.get('opta_shotevents', pd.DataFrame())
    if df_raw.empty:
        df_raw = dp.get('playerstats', pd.DataFrame())

    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # --- DATA RENS ---
    # Sørg for kolonnenavne er store pga. Snowflake
    df_raw.columns = [c.upper() for c in df_raw.columns]
    
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt').astype(str)

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    # --- TAB 1: AFSLUTNINGER (UÆNDRET) ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        with col_ctrl:
            spiller_liste = sorted(df_hif['PLAYER_NAME'].unique().tolist())
            v_spiller_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            
            df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
            if v_spiller_skud != "Hele Holdet":
                df_skud = df_skud[df_skud['PLAYER_NAME'] == v_spiller_skud]
            
            df_skud['ER_MAAL'] = df_skud['TYPE_STR'] == '16'
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
                <div class="stat-box">
                    <div class="stat-label">xG Kvalitet</div>
                    <div class="stat-value">{df_skud['XG_VAL'].sum() if 'XG_VAL' in df_skud.columns else 0.00:.2f}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(7.5, 9.5))
            if not df_skud.empty:
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'],
                             s=100,
                             c=df_skud['ER_MAAL'].map({True: HIF_RED, False: 'white'}),
                             edgecolors=HIF_RED, linewidth=1.2, alpha=0.9, ax=ax)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 2: ASSISTS (OPDATERET LOGIK) ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        with col_ctrl_a:
            v_spiller_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_assist")
            
            # Bruger dine nye SQL-flag til filtrering
            mask_chance = (df_hif['EVENT_TYPEID'] == 1) & (
                (df_hif.get('IS_ASSIST', 0) == 1) | 
                (df_hif.get('IS_KEY_PASS', 0) == 1) | 
                (df_hif.get('IS_2ND_ASSIST', 0) == 1)
            )
            df_chance = df_hif[mask_chance].copy()
            
            if v_spiller_a != "Hvidovre IF":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_spiller_a]
            
            # Præcis optælling: Assist (210), Key Pass (29 men ikke 210), 2nd Assist (211)
            n_assist = int(df_chance.get('IS_ASSIST', 0).sum())
            n_key = int((df_chance.get('IS_KEY_PASS', 0) == 1) & (df_chance.get('IS_ASSIST', 0) == 0)).sum()
            n_2nd = int(df_chance.get('IS_2ND_ASSIST', 0).sum())

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
                # Arrows bruger de nye koordinater fra SQL
                pitch_a.arrows(df_chance['EVENT_X'], df_chance['EVENT_Y'],
                               df_chance['PASS_END_X'].astype(float), df_chance['PASS_END_Y'].astype(float),
                               color='#eeeeee', width=2, headwidth=3, headlength=3, ax=ax_a, zorder=1)
                
                def assign_color(row):
                    if row.get('IS_ASSIST') == 1: return HIF_GOLD
                    if row.get('IS_2ND_ASSIST') == 1: return HIF_BLUE
                    return '#999999'
                
                df_chance['COLOR'] = df_chance.apply(assign_color, axis=1)
                pitch_a.scatter(df_chance['EVENT_X'], df_chance['EVENT_Y'], 
                                s=110, color=df_chance['COLOR'], edgecolors='white', 
                                linewidth=1.2, ax=ax_a, zorder=2)
            st.pyplot(fig_a, use_container_width=True)
