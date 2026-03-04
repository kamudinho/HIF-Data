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
    # --- TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:1px; border-radius:2px; margin-bottom:1px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">DATA ANALYSE</h3>
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

    tab1, tab2 = st.tabs(["Afslutninger", "Assists"])

    # --- TAB 1: SKUDKORT ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        
        with col_ctrl:
            st.write("### AFSLUTNINGER")
            spiller_liste = sorted(df_hif['PLAYER_NAME'].unique().tolist())
            v_spiller_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            
            df_skud = df_hif[df_hif['TYPE_STR'].isin(['13', '14', '15', '16'])].copy()
            if v_spiller_skud != "Hele Holdet":
                df_skud = df_skud[df_skud['PLAYER_NAME'] == v_spiller_skud]
            
            df_skud['ER_MAAL'] = df_skud['TYPE_STR'] == '16'
            
            st.markdown("---")
            # Legend for skud
            st.markdown(f"<span style='color:{HIF_RED}; font-size:20px;'>●</span> **Mål**: {int(df_skud['ER_MAAL'].sum())}", unsafe_allow_html=True)
            st.markdown(f"<span style='border:1px solid {HIF_RED}; border-radius:50%; width:12px; height:12px; display:inline-block;'></span> **Øvrige skud**: {len(df_skud) - int(df_skud['ER_MAAL'].sum())}", unsafe_allow_html=True)
            st.markdown(f"**xG Total**: {df_skud['XG_VAL'].sum():.2f}")

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(8, 10))
            if not df_skud.empty:
                pitch.scatter(df_skud['EVENT_X'], df_skud['EVENT_Y'],
                             s=(df_skud['XG_VAL'] * 1000) + 60,
                             c=df_skud['ER_MAAL'].map({True: HIF_RED, False: 'white'}),
                             edgecolors=HIF_RED, linewidth=1.2, alpha=0.8, ax=ax)
            st.pyplot(fig)

    # --- TAB 2: ASSISTS ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        
        with col_ctrl_a:
            st.write("### CHANCER")
            v_spiller_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_assist")
            
            mask_chance = (df_hif['QUAL_STR'].str.contains('210|29|211', na=False)) & (df_hif['TYPE_STR'] == '1')
            df_chance = df_hif[mask_chance].copy()
            
            if v_spiller_a != "Hvidovre IF":
                df_chance = df_chance[df_chance['PLAYER_NAME'] == v_spiller_a]
            
            st.markdown("---")
            # Stats med farvede prikker foran ordet
            n_assist = df_chance['QUAL_STR'].str.contains('210').sum()
            n_key = df_chance['QUAL_STR'].str.contains('29').sum()
            n_2nd = df_chance['QUAL_STR'].str.contains('211').sum()
            
            st.markdown(f"<span style='color:{HIF_GOLD}; font-size:20px;'>●</span> **Assists**: {n_assist}", unsafe_allow_html=True)
            st.markdown(f"<span style='color:#999999; font-size:20px;'>●</span> **Key Passes**: {n_key}", unsafe_allow_html=True)
            st.markdown(f"<span style='color:{HIF_BLUE}; font-size:20px;'>●</span> **2nd Assists**: {n_2nd}", unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
            
            if not df_chance.empty:
                pitch_a.arrows(df_chance['EVENT_X'], df_chance['EVENT_Y'],
                               df_chance['PASS_END_X'].fillna(95), df_chance['PASS_END_Y'].fillna(50),
                               color='#dddddd', width=2, headwidth=3, headlength=3, ax=ax_a, zorder=1)
                
                def get_color(q):
                    if '210' in q: return HIF_GOLD
                    if '211' in q: return HIF_BLUE
                    return '#999999'
                
                df_chance['COLOR'] = df_chance['QUAL_STR'].apply(get_color)
                pitch_a.scatter(df_chance['EVENT_X'], df_chance['EVENT_Y'], 
                                s=120, color=df_chance['COLOR'], edgecolors='white', 
                                linewidth=1, ax=ax_a, zorder=2)
            
            st.pyplot(fig_a)
