import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
HIF_OPTA_UUID = "8gxd9ry2580pu1b1dd5ny9ymy"

def vis_side(dp):
    # 1. CSS Styling
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 10px 15px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 8px; }
            .stat-label { font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }
            .stat-value { font-size: 1.6rem; font-weight: 800; color: #1a1a1a; margin-left: 5px; }
        </style>
    """, unsafe_allow_html=True)
    
    # 2. Hent og Rens Data
    df_raw = dp.get('playerstats', pd.DataFrame())
    
    if df_raw.empty:
        st.error("❌ Datapakken er tom. Tjek din Snowflake-forbindelse.")
        return

    # Tving data til HIF (Case-insensitive match på UUID)
    df_hif = df_raw[df_raw['EVENT_CONTESTANT_OPTAUUID'].astype(str).str.lower().str.strip() == HIF_OPTA_UUID.lower()].copy()

    if df_hif.empty:
        st.warning(f"⚠️ Ingen data fundet for HIF ({HIF_OPTA_UUID}). Viser alt data for at undgå tom skærm.")
        df_hif = df_raw.copy()

    # Konvertér alle vigtige kolonner til tal med det samme
    cols_to_fix = ['EVENT_X', 'EVENT_Y', 'PASS_X', 'PASS_Y', 'XG_VAL', 'EVENT_TYPEID', 'IS_ASSIST', 'EVENT_OUTCOME']
    for col in cols_to_fix:
        if col in df_hif.columns:
            df_hif[col] = pd.to_numeric(df_hif[col], errors='coerce').fillna(0)

    df_hif['PLAYER_NAME'] = df_hif['PLAYER_NAME'].fillna('Ukendt')

    tab1, tab2 = st.tabs(["AFSLUTNINGER", "CHANCESKABELSE"])

    # --- TAB 1: AFSLUTNINGER (MÅL & SKUD) ---
    with tab1:
        col_viz, col_ctrl = st.columns([3, 1])
        # Filter for skud-events
        df_skud = df_hif[df_hif['EVENT_TYPEID'].isin([13, 14, 15, 16])].copy()
        
        with col_ctrl:
            spiller_liste = sorted(df_skud['PLAYER_NAME'].unique().tolist())
            v_skud = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste, key="sb_skud")
            df_skud_vis = df_skud if v_skud == "Hele Holdet" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
            
            n_goals = int((df_skud_vis["EVENT_TYPEID"] == 16).sum())
            
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(df_skud_vis)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{n_goals}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">xG</div><div class="stat-value">{df_skud_vis["XG_VAL"].sum():.2f}</div></div>', unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(7, 9))
            if not df_skud_vis.empty:
                # Farv mål røde, resten hvide
                c_map = (df_skud_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_skud_vis['EVENT_X'], df_skud_vis['EVENT_Y'], 
                              s=df_skud_vis['XG_VAL']*800 + 50, 
                              c=c_map, edgecolors=HIF_RED, linewidth=1.2, ax=ax, zorder=3)
            st.pyplot(fig)

    # --- TAB 2: CHANCESKABELSE (ASSISTS & KEY PASSES) ---
    with tab2:
        col_viz_a, col_ctrl_a = st.columns([3, 1])
        
        # Filtrér for handlinger der førte til et skud (hvor vi har pass-koordinater)
        df_a = df_hif[df_hif['PASS_X'] > 0].copy()

        with col_ctrl_a:
            spiller_liste_a = sorted(df_a['PLAYER_NAME'].unique().tolist())
            v_a = st.selectbox("Vælg spiller", options=["Hele Holdet"] + spiller_liste_a, key="sb_assist")
            df_a_vis = df_a if v_a == "Hele Holdet" else df_a[df_a['PLAYER_NAME'] == v_a]
            
            # Definer assists: IS_ASSIST er markeret og skuddet blev mål (16)
            mask_goal_assist = (df_a_vis['IS_ASSIST'] == 1) & (df_a_vis['EVENT_TYPEID'] == 16)
            n_assists = int(mask_goal_assist.sum())
            n_key_passes = len(df_a_vis) - n_assists
            
            st.markdown(f'<div class="stat-box"><div class="stat-label">Goal Assists</div><div class="stat-value">{n_assists}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Shot Assists</div><div class="stat-value">{n_key_passes}</div></div>', unsafe_allow_html=True)

        with col_viz_a:
            pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig_a, ax_a = pitch_a.draw(figsize=(7, 9))
            
            if not df_a_vis.empty:
                # 1. Tegn pile (fra pass-start til skud-punkt)
                # Goal Assists bliver tykkere og røde/guld, Shot Assists bliver tynde og grå
                for _, row in df_a_vis.iterrows():
                    is_goal = (row['IS_ASSIST'] == 1 and row['EVENT_TYPEID'] == 16)
                    line_color = HIF_GOLD if is_goal else '#dddddd'
                    line_width = 3 if is_goal else 1.5
                    
                    pitch_a.arrows(row['PASS_X'], row['PASS_Y'], row['EVENT_X'], row['EVENT_Y'],
                                   color=line_color, width=line_width, headwidth=4, ax=ax_a, zorder=2)
                
                # 2. Marker slutpunktet (hvor skuddet faldt)
                dot_colors = mask_goal_assist.map({True: HIF_GOLD, False: '#999999'})
                pitch_a.scatter(df_a_vis['EVENT_X'], df_a_vis['EVENT_Y'], s=100, 
                                color=dot_colors, edgecolors='white', linewidth=1, ax=ax_a, zorder=3)
            
            st.pyplot(fig_a)
