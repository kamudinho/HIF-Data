import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b' 
DZ_COLOR = '#1f77b4'

def vis_side(dp):
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 8px; }
            .stat-label { font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }
            .stat-value { font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }
            .legend-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
            .stTabs [data-baseweb="tab-panel"] { padding-top: 10px; }
        </style>
    """, unsafe_allow_html=True)
    
    df_skud = dp.get('playerstats', pd.DataFrame()).copy()
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    
    if not df_skud.empty:
        df_skud['IS_DZ_GEO'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)
    else:
        df_skud['IS_DZ_GEO'] = False

    tab1, tab2, tab3 = st.tabs(["AFSLUTNINGER", "DANGER ZONE", "ASSISTS"])

    # Fælles indstilling for prikstørrelse
    DOT_SIZE = 90 
    LINE_WIDTH = 1.2

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        if df_skud.empty:
            st.info("Ingen skuddata fundet.")
        else:
            col_viz, col_ctrl = st.columns([2.2, 1]) # Gør banen lidt smallere
            with col_ctrl:
                spiller_liste = sorted(df_skud['PLAYER_NAME'].unique())
                v_skud = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_skud")
                df_vis = df_skud if v_skud == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
                
                st.markdown(f"""
                    <div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background-color:white; border:2px solid {HIF_RED};"></span>Skud i alt</div><div class="stat-value">{len(df_vis)}</div></div>
                    <div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background-color:{HIF_RED};"></span>Mål</div><div class="stat-value">{len(df_vis[df_vis["EVENT_TYPEID"]==16])}</div></div>
                """, unsafe_allow_html=True)

            with col_viz:
                pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig, ax = pitch.draw(figsize=(5.5, 7.5)) # Reduceret størrelse
                c_map = (df_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                # Her låser vi s=DOT_SIZE så de ikke ændrer sig
                pitch.scatter(df_vis['EVENT_X'], df_vis['EVENT_Y'], s=DOT_SIZE, c=c_map, edgecolors=HIF_RED, linewidth=LINE_WIDTH, ax=ax)
                st.pyplot(fig)

    # --- TAB 2: DANGER ZONE ---
    with tab2:
        if df_skud.empty:
            st.info("Ingen data fundet.")
        else:
            col_dz_viz, col_dz_ctrl = st.columns([2.2, 1])
            total_skud_hif = len(df_skud)
            dz_skud_hif = len(df_skud[df_skud['IS_DZ_GEO']])
            hif_dz_pct = (dz_skud_hif / total_skud_hif * 100) if total_skud_hif > 0 else 0

            with col_dz_ctrl:
                spiller_liste_dz = sorted(df_skud['PLAYER_NAME'].unique())
                v_dz = st.selectbox("Vælg spiller (DZ)", options=["Hvidovre IF"] + spiller_liste_dz, key="sb_dz")
                df_dz_full = df_skud if v_dz == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_dz]
                dz_hits = df_dz_full[df_dz_full['IS_DZ_GEO']].copy()
                dz_goals = len(dz_hits[dz_hits['EVENT_TYPEID'] == 16])
                spiller_dz_pct = (len(dz_hits) / len(df_dz_full) * 100) if len(df_dz_full) > 0 else 0
                
                st.markdown(f"""
                    <div class="stat-box" style="border-left-color: {DZ_COLOR}"><div class="stat-label"><span class="legend-dot" style="background-color:white; border:2px solid {HIF_RED};"></span>Skud i DZ</div><div class="stat-value">{len(dz_hits)}</div></div>
                    <div class="stat-box" style="border-left-color: {HIF_RED}"><div class="stat-label"><span class="legend-dot" style="background-color:{HIF_RED};"></span>Mål i DZ</div><div class="stat-value">{dz_goals}</div></div>
                    <div class="stat-box" style="border-left-color: #333;"><div class="stat-label">HIF i DZ</div><div class="stat-value">{hif_dz_pct:.1f}%</div></div>
                    <div class="stat-box" style="border-left-color: {HIF_GOLD}"><div class="stat-label">Spiller i DZ</div><div class="stat-value">{spiller_dz_pct:.1f}%</div></div>
                """, unsafe_allow_html=True)

            with col_dz_viz:
                pitch_dz = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                # Vi gør figuren lidt højere her for at give plads til tabellen nedenunder
                fig_dz, ax_dz = pitch_dz.draw(figsize=(6, 8)) 
                ax_dz.set_ylim(70, 102) 
                
                # Danger Zone rektangel
                dz_rect = patches.Rectangle((37, 88.5), 26, 11.5, linewidth=1.5, edgecolor=DZ_COLOR, facecolor=DZ_COLOR, alpha=0.1, linestyle='--', zorder=1)
                ax_dz.add_patch(dz_rect)
                
                # VI PLOTTER KUN SKUD INDE I DZ NU:
                if not dz_hits.empty:
                    c_dz = (dz_hits['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                    pitch_dz.scatter(dz_hits['EVENT_X'], dz_hits['EVENT_Y'], s=DOT_SIZE, c=c_dz, edgecolors=HIF_RED, linewidth=LINE_WIDTH, ax=ax_dz, zorder=2)
                
                st.pyplot(fig_dz)

            # --- TABEL TILPASNING ---
            stats_list = []
            for spiller in spiller_liste_dz:
                s_data = df_skud[df_skud['PLAYER_NAME'] == spiller]
                s_dz = s_data[s_data['IS_DZ_GEO']]
                if len(s_dz) > 0: # Vi viser kun spillere i tabellen, der faktisk HAR skud i DZ
                    efternavn = spiller.split()[-1] if isinstance(spiller, str) else spiller
                    stats_list.append({
                        "Navn": efternavn, 
                        "Skud": len(s_dz), 
                        "Mål": len(s_dz[s_dz['EVENT_TYPEID'] == 16]), 
                        "DZ %": (len(s_dz)/len(s_data)*100) if len(s_data) > 0 else 0
                    })
            
            if stats_list:
                df_table_data = pd.DataFrame(stats_list).sort_values("Skud", ascending=False)
                
                # Vi øger bredden på figuren (12) og justerer højden dynamisk
                fig_tab, ax_tab = plt.subplots(figsize=(12, 3)) 
                ax_tab.axis('off')
                
                the_table = ax_tab.table(
                    cellText=[
                        [int(v) for v in df_table_data['Skud'].values], 
                        [int(v) for v in df_table_data['Mål'].values], 
                        [f"{v:.1f}%" for v in df_table_data['DZ %'].values]
                    ], 
                    rowLabels=["Skud i DZ", "Mål i DZ", "DZ %"], 
                    colLabels=df_table_data['Navn'].values, 
                    loc='center', 
                    cellLoc='center'
                )
                
                the_table.auto_set_font_size(False)
                the_table.set_fontsize(8)
                the_table.scale(1.1, 2.2) # Gør rækkerne højere og lettere at læse
                
                # Styling af header og navne
                for (row, col), cell in the_table.get_celld().items():
                    if row == 0: # Spillernavne
                        cell.set_text_props(rotation=270, ha='center', va='center')
                        cell.set_height(0.4)
                    if col == -1: # Række-labels
                        cell.set_facecolor('#f2f2f2')
                        cell.set_text_props(weight='bold')

                plt.tight_layout()
                st.pyplot(fig_tab)

    # --- TAB 3: ASSISTS ---
    with tab3:
        if df_assists.empty:
            st.warning("⚠️ Ingen assists fundet.")
        else:
            col_viz_a, col_ctrl_a = st.columns([2.2, 1])
            with col_ctrl_a:
                spiller_liste_a = sorted([s for s in df_assists['ASSIST_PLAYER'].unique() if pd.notna(s)])
                v_a = st.selectbox("Vælg spiller (Assists)", options=["Hvidovre IF"] + spiller_liste_a, key="sb_assist")
                df_a_vis = df_assists if v_a == "Hvidovre IF" else df_assists[df_assists['ASSIST_PLAYER'] == v_a]
                
                st.markdown(f"""
                    <div class="stat-box">
                        <div class="stat-label">
                            <span class="legend-dot" style="background-color:{HIF_GOLD}; border:1px solid black;"></span>
                            Goal Assists
                        </div>
                        <div class="stat-value">{len(df_a_vis)}</div>
                    </div>
                """, unsafe_allow_html=True)

            with col_viz_a:
                pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig_a, ax_a = pitch_a.draw(figsize=(5.5, 7.5))
                if not df_a_vis.empty:
                    pitch_a.arrows(df_a_vis['PASS_START_X'], df_a_vis['PASS_START_Y'], 
                                   df_a_vis['SHOT_X'], df_a_vis['SHOT_Y'], 
                                   color='#888888', alpha=0.5, width=1.5, headwidth=3, ax=ax_a, zorder=1)
                    pitch_a.scatter(df_a_vis['PASS_START_X'], df_a_vis['PASS_START_Y'], 
                                    s=DOT_SIZE, color=HIF_GOLD, edgecolors='black', linewidth=1, ax=ax_a, zorder=2)
                st.pyplot(fig_a)
