import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_BLUE = '#0056a3'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"
hif_rod = "#df003b"

def vis_side(dp, logo_map=None):
    # --- CUSTOM CSS FOR LÆSBARHED ---
    st.markdown("""
        <style>
            .stat-box {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 10px;
                border-left: 5px solid #df003b;
                margin-bottom: 12px;
            }
            .stat-label {
                font-size: 0.85rem;
                text-transform: uppercase;
                color: #666;
                font-weight: bold;
                display: flex;
                align-items: center;
                letter-spacing: 0.5px;
            }
            .stat-value {
                font-size: 1.8rem;
                font-weight: 800;
                color: #1a1a1a;
                margin-left: 25px;
                line-height: 1.2;
            }
            .dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 10px; }
            /* Fjerner Streamlit padding i toppen af tabs */
            .stTabs [data-baseweb="tab-panel"] { padding-top: 1rem; }
        </style>
    """, unsafe_allow_html=True)

    # --- TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:8px; border-radius:4px; margin-bottom:15px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:2px; font-size:1.1rem;">DATA ANALYSE</h3>
        </div>
    """, unsafe_allow_html=True)
    
    df_raw = dp.get('playerstats', pd.DataFrame()) if isinstance(dp, dict) else dp
    if df_raw.empty:
        st.info("Ingen kampdata fundet.")
        return

    # --- DATA RENS ---
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()
    df_hif['TYPE_STR'] = df_hif['EVENT_TYPEID'].astype(str).str.replace('.0', '', regex=False).str.strip()
    df_hif['QUAL_STR'] = df_hif['QUALIFIERS'].astype(str)
    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt').astype(str)

    # Rene tabs uden ikoner
    tab1, tab2 = st.tabs(["AFSLUTNINGER", "ASSISTS"])

    # --- TAB 1: SKUDKORT ---
    with tab1:
        col_viz, col_ctrl = st.columns([2.8, 1])
        
        with col_ctrl:
            st.markdown("### AFSLUTNINGER")
            spiller_liste = sorted(df_hif['PLAYER_NAME'].unique().tolist())
            v_spiller_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            
            df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
            if v_spiller_skud != "Hele Holdet":
                df_skud = df_skud[df_skud['PLAYER_NAME'] == v_spiller_skud]
            
            df_skud['ER_MAAL'] = df_skud['TYPE_STR'] == '16'
            n_maal = int(df_skud['ER_MAAL'].sum())
            n_skud = len(df_skud)

            st.markdown("<br>", unsafe_allow_html=True)
            
            # Afslutninger først, så Mål
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:white; border:2px solid {HIF_RED}"></span> Afslutninger</div>
                    <div class="stat-value">{n_skud}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label"><span class="dot" style="background-color:{HIF_RED}"></span> Mål</div>
                    <div class="stat-value">{n_maal}</div>
                </div>
                <div class="stat-box">
                    <div class="stat-label">xG Kvalitet</div>
                    <div class="stat-value">{df_skud['XG_VAL'].sum():.2f}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(8, 10))
            if not df_skud.empty:
                # Cirkler: Mål er fyldte, brændte er hvide med rød kant
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'],
                             s=(df_skud['XG_VAL'] * 1100) + 70,
                             c=df_skud['ER_MAAL'].map({True: HIF_RED, False: 'white'}),
                             edgecolors=HIF_RED, linewidth=1.5, alpha=0.9, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: ASSISTS ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([2.8, 1])
        
        with col_ctrl_a:
            st.markdown("### CHANCER")
            v_spiller_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_assist")
            
            mask_chance = (df_hif['QUAL_STR'].str.contains('210|29|211', na=False)) & (df_hif['TYPE_STR'] == '1')
            df_chance = df_hif[mask_chance].copy()
            
            if v_spiller_a != "Hvidovre IF":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_spiller_a]
            
            n_assist = df_chance['QUAL_STR'].str.contains('210').sum()
            n_key = df_chance['QUAL_STR'].str.contains('29').sum()
            n_2nd = df_chance['QUAL_STR'].str.contains('211').sum()

            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown(f"""
                <div class="stat-box">
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
            fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
            
            if not df_chance.empty:
                pitch_a.arrows(df_chance['EVENT_X'], df_chance['EVENT_Y'],
                               df_chance['PASS_END_X'].fillna(95), df_chance['PASS_END_Y'].fillna(50),
                               color='#eeeeee', width=2, headwidth=3, headlength=3, ax=ax_a, zorder=1)
                
                def get_color(q):
                    if '210' in q: return HIF_GOLD
                    if '211' in q: return HIF_BLUE
                    return '#999999'
                
                df_chance['COLOR'] = df_chance['QUAL_STR'].apply(get_color)
                pitch_a.scatter(df_chance['EVENT_X'], df_chance['EVENT_Y'], 
                                s=130, color=df_chance['COLOR'], edgecolors='white', 
                                linewidth=1.5, ax=ax_a, zorder=2)
            st.pyplot(fig_a)
