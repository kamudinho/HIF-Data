import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp):
    df_debug = dp.get('playerstats', pd.DataFrame())
    if not df_debug.empty:
        st.sidebar.write("✅ Data modtaget fra Snowflake")
        st.sidebar.write(f"Antal rækker: {len(df_debug)}")
        st.sidebar.write(f"Kolonner: {df_debug.columns.tolist()}")
    else:
        st.sidebar.error("❌ Ingen data modtaget i dp['playerstats']")
    # CSS Styling
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 10px 15px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 8px; }
            .stat-label { font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }
            .stat-value { font-size: 1.6rem; font-weight: 800; color: #1a1a1a; margin-left: 5px; }
        </style>
    """, unsafe_allow_html=True)
    
    # Hent data
    df_hif = dp.get('playerstats', pd.DataFrame())
    
    if df_hif.empty:
        st.info("Ingen kampdata fundet for Hvidovre IF.")
        return

    # --- ROBUST FILTER LOGIK ---
    # Vi finder dynamisk det UUID der optræder oftest i datasættet 
    # (Dette sikrer at appen virker uanset om UUID'et ændrer sig i Snowflake)
    try:
        if not df_hif['EVENT_CONTESTANT_OPTAUUID'].empty:
            auto_hif_uuid = df_hif['EVENT_CONTESTANT_OPTAUUID'].value_counts().idxmax()
            df_hif = df_hif[df_hif['EVENT_CONTESTANT_OPTAUUID'] == auto_hif_uuid].copy()
            st.sidebar.success(f"Viser data for ID: {auto_hif_uuid}")
    except Exception:
        # Fallback til din hardcodede værdi hvis ovenstående fejler
        df_hif = df_hif[df_hif['EVENT_CONTESTANT_OPTAUUID'] == HIF_OPTA_UUID].copy()

    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt')

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "CHANCESKABELSE"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        df_skud = df_hif[df_hif['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        
        with col_ctrl:
            spiller_liste = sorted(df_skud['PLAYER_NAME'].unique().tolist())
            v_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            df_skud_vis = df_skud if v_skud == "Hele Holdet" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
            
            # RETTELSE 1: .sum() flyttet ind før int()
            n_goals = (df_skud_vis["EVENT_TYPEID"] == 16).sum()
            
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(df_skud_vis)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{int(n_goals)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">xG</div><div class="stat-value">{df_skud_vis["XG_VAL"].sum():.2f}</div></div>', unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(7, 9))
            if not df_skud_vis.empty:
                c_map = (df_skud_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_skud_vis['EVENT_X'], df_skud_vis['EVENT_Y'], 
                              s=df_skud_vis['XG_VAL']*1000+50, 
                              c=c_map, edgecolors=HIF_RED, linewidth=1.2, ax=ax, zorder=3)
            st.pyplot(fig)

    # --- TAB 2: CHANCESKABELSE ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        df_a = df_hif[df_hif['PASS_X'] > 0].copy()

        with col_ctrl_a:
            spiller_liste_a = sorted(df_a['PLAYER_NAME'].unique().tolist())
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste_a, key="sb_assist")
            df_a_vis = df_a if v_a == "Hvidovre IF" else df_a[df_a['PLAYER_NAME'] == v_a]
            
            # RETTELSE 2: .sum() flyttet ind i int() parentesen
            n_ass = int(((df_a_vis['IS_ASSIST'] == 1) & (df_a_vis['EVENT_OUTCOME'] == 1)).sum())
            
            st.markdown(f'<div class="stat-box"><div class="stat-label">Assists</div><div class="stat-value">{n_ass}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Key Passes</div><div class="stat-value">{len(df_a_vis)-n_ass}</div></div>', unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7, 9))
            
            if not df_a_vis.empty:
                pitch_a.arrows(df_a_vis['PASS_X'], df_a_vis['PASS_Y'], 
                               df_a_vis['EVENT_X'], df_a_vis['EVENT_Y'], 
                               color='#dddddd', width=2, headwidth=3, ax=ax_a, zorder=1)
                
                dot_colors = df_a_vis['IS_ASSIST'].map({1: HIF_GOLD, 0: '#999999'})
                pitch_a.scatter(df_a_vis['EVENT_X'], df_a_vis['EVENT_Y'], s=120, 
                                color=dot_colors, edgecolors='white', linewidth=1.2, ax=ax_a, zorder=2)
            st.pyplot(fig_a)
