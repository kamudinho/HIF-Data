import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
DZ_COLOR = '#1f77b4'

hif_id = TEAMS["Hvidovre"]["opta_uuid"]

def vis_side(dp):
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 5px solid #b8860b; margin-bottom: 8px; }
            .stat-label { font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }
            .stat-value { font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }
            .legend-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
        </style>
    """, unsafe_allow_html=True)
    
    # Hent data
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    
    if df_assists.empty:
        st.warning("⚠️ Ingen assist-data fundet for denne periode.")
        return

    # Tabs definition
    tab1, tab2 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP"])

    DOT_SIZE = 90 
    LINE_WIDTH = 1.2

    # --- TAB 1: SPILLEROVERSIGT (STATISTIK) ---
    with tab1:
        st.subheader("Assist & Kreativitet")
        
        # Aggregering af spillerdata
        spiller_stats = []
        alle_spillere = sorted([s for s in df_assists['ASSIST_PLAYER'].unique() if pd.notna(s)])
        
        for spiller in alle_spillere:
            s_data = df_assists[df_assists['ASSIST_PLAYER'] == spiller]
            
            # Her kan du tilføje xA hvis det findes i dit datasæt
            total_assists = len(s_data)
            # Find ud af hvor mange af disse der førte til mål (hvis din df har en mål-indikator)
            # Her antager vi at 'df_assists' i sig selv er Key Passes/Assists
            
            spiller_stats.append({
                "Spiller": spiller.split()[-1],
                "Assists": total_assists,
                "Primære Zoner": s_data['PASS_TYPE'].mode()[0] if 'PASS_TYPE' in s_data else "Open Play"
            })
        
        if spiller_stats:
            df_table = pd.DataFrame(spiller_stats).sort_values("Assists", ascending=False)
            
            st.dataframe(
                df_table,
                column_config={
                    "Spiller": st.column_config.TextColumn("Spiller"),
                    "Assists": st.column_config.NumberColumn("Antal Assists", format="%d"),
                    "Primære Zoner": st.column_config.TextColumn("Type")
                },
                hide_index=True,
                use_container_width=True
            )

    # --- TAB 2: ASSIST-MAP (VISUELT) ---
    with tab2:
        col_viz, col_ctrl = st.columns([2.2, 1])
        
        with col_ctrl:
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + alle_spillere, key="sb_assist_map")
            df_vis = df_assists if v_a == "Hvidovre IF" else df_assists[df_assists['ASSIST_PLAYER'] == v_a]
            
            st.markdown(f"""
                <div class="stat-box">
                    <div class="stat-label"><span class="legend-dot" style="background-color:{HIF_GOLD};"></span>Total Assists</div>
                    <div class="stat-value">{len(df_vis)}</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.caption("Pilen viser afleveringens retning. Prikken er startpositionen.")

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(6, 8))
            
            if not df_vis.empty:
                # Tegn pile for afleveringerne
                pitch.arrows(
                    df_vis['PASS_START_X'], df_vis['PASS_START_Y'],
                    df_vis['SHOT_X'], df_vis['SHOT_Y'],
                    color=HIF_GOLD, alpha=0.6, width=2, headwidth=3, 
                    ax=ax, zorder=1, label='Assist'
                )
                
                # Prik ved startpunktet
                pitch.scatter(
                    df_vis['PASS_START_X'], df_vis['PASS_START_Y'],
                    s=DOT_SIZE, color='white', edgecolors=HIF_GOLD, 
                    linewidth=2, ax=ax, zorder=2
                )
            
            st.pyplot(fig)
