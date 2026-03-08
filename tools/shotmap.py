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
            .stat-box { background-color: #f8f9fa; padding: 10px 15px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 8px; }
            .stat-label { font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }
            .stat-value { font-size: 1.6rem; font-weight: 800; color: #1a1a1a; margin-left: 5px; }
            .stTabs [data-baseweb="tab-panel"] { padding-top: 10px; }
        </style>
    """, unsafe_allow_html=True)
    
    df_skud = dp.get('playerstats', pd.DataFrame()).copy()
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    
    if not df_skud.empty:
        df_skud['IS_DZ_GEO'] = (
            (df_skud['EVENT_X'] >= 88.5) & 
            (df_skud['EVENT_Y'] >= 37.0) & 
            (df_skud['EVENT_Y'] <= 63.0)
        )
    else:
        df_skud['IS_DZ_GEO'] = False

    tab1, tab2, tab3 = st.tabs(["AFSLUTNINGER", "DANGER ZONE", "ASSISTS"])

    # --- TAB 1: AFSLUTNINGER ---
    with tab1:
        if df_skud.empty:
            st.info("Ingen skuddata fundet.")
        else:
            col_viz, col_ctrl = st.columns([3, 1])
            with col_ctrl:
                spiller_liste = sorted(df_skud['PLAYER_NAME'].unique())
                v_skud = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + spiller_liste, key="sb_skud")
                df_vis = df_skud if v_skud == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == v_skud]
                st.markdown(f'<div class="stat-box"><div class="stat-label">Skud i alt</div><div class="stat-value">{len(df_vis)}</div></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(df_vis[df_vis["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)

            with col_viz:
                pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig, ax = pitch.draw(figsize=(8, 10))
                c_map = (df_vis['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch.scatter(df_vis['EVENT_X'], df_vis['EVENT_Y'], s=150, c=c_map, edgecolors=HIF_RED, linewidth=1.5, ax=ax)
                
                # Legend for Afslutninger
                ax.scatter(5, 60, s=100, c=HIF_RED, edgecolors=HIF_RED, transform=ax.transAxes)
                ax.text(8, 60, 'Mål', va='center', fontsize=10, transform=ax.transAxes)
                ax.scatter(5, 55, s=100, c='white', edgecolors=HIF_RED, linewidth=1.5, transform=ax.transAxes)
                ax.text(8, 55, 'Skud', va='center', fontsize=10, transform=ax.transAxes)
                
                st.pyplot(fig)

    # --- TAB 2: DANGER ZONE ---
    with tab2:
        if df_skud.empty:
            st.info("Ingen data fundet.")
        else:
            col_dz_viz, col_dz_ctrl = st.columns([3, 1])
            total_skud_hif = len(df_skud)
            dz_skud_hif = len(df_skud[df_skud['IS_DZ_GEO']])
            hif_dz_pct = (dz_skud_hif / total_skud_hif * 100) if total_skud_hif > 0 else 0

            with col_dz_ctrl:
                spiller_liste_dz = sorted(df_skud['PLAYER_NAME'].unique())
                v_dz = st.selectbox("Vælg spiller (DZ)", options=["Hvidovre IF"] + spiller_liste_dz, key="sb_dz")
                df_dz_full = df_skud if v_dz == "Hvidovre IF" else df_skud[df_dz_full['PLAYER_NAME'] == v_dz]
                dz_hits = df_dz_full[df_dz_full['IS_DZ_GEO']].copy()
                dz_goals = len(dz_hits[dz_hits['EVENT_TYPEID'] == 16])
                spiller_dz_pct = (len(dz_hits) / len(df_dz_full) * 100) if len(df_dz_full) > 0 else 0
                
                # Stat-bokse med indbyggede legends (farvede prikker)
                st.markdown(f"""
                    <div class="stat-box" style="border-left-color: {DZ_COLOR}">
                        <div class="stat-label">
                            <span style="height: 10px; width: 10px; background-color: white; border: 2px solid {HIF_RED}; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>
                            Skud i DZ
                        </div>
                        <div class="stat-value">{len(dz_hits)}</div>
                    </div>
                    <div class="stat-box" style="border-left-color: {HIF_RED}">
                        <div class="stat-label">
                            <span style="height: 10px; width: 10px; background-color: {HIF_RED}; border-radius: 50%; display: inline-block; margin-right: 5px;"></span>
                            Mål i DZ
                        </div>
                        <div class="stat-value">{dz_goals}</div>
                    </div>
                    <div class="stat-box" style="border-left-color: #333;">
                        <div class="stat-label">HIF samlet i DZ</div>
                        <div class="stat-value">{hif_dz_pct:.1f}%</div>
                    </div>
                    <div class="stat-box" style="border-left-color: {HIF_GOLD}">
                        <div class="stat-label">Spiller samlet i DZ</div>
                        <div class="stat-value">{spiller_dz_pct:.1f}%</div>
                    </div>
                """, unsafe_allow_html=True)

            with col_dz_viz:
                pitch_dz = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig_dz, ax_dz = pitch_dz.draw(figsize=(8, 7))
                ax_dz.set_ylim(70, 102) 
                dz_rect = patches.Rectangle((37, 88.5), 26, 11.5, linewidth=2, edgecolor=DZ_COLOR, facecolor=DZ_COLOR, alpha=0.15, linestyle='--', zorder=1)
                ax_dz.add_patch(dz_rect)
                
                non_dz = df_dz_full[~df_dz_full['IS_DZ_GEO']]
                pitch_dz.scatter(non_dz['EVENT_X'], non_dz['EVENT_Y'], s=70, c='white', edgecolors='#dddddd', alpha=0.2, ax=ax_dz)
                c_dz = (dz_hits['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                pitch_dz.scatter(dz_hits['EVENT_X'], dz_hits['EVENT_Y'], s=200, c=c_dz, edgecolors=HIF_RED, linewidth=2, ax=ax_dz)
                
                # Legend for DZ
                ax_dz.scatter(5, 15, s=100, c=HIF_RED, edgecolors=HIF_RED, transform=ax_dz.transAxes)
                ax_dz.text(8, 15, 'Mål i DZ', va='center', fontsize=9, transform=ax_dz.transAxes)
                ax_dz.scatter(5, 8, s=100, c='white', edgecolors=HIF_RED, linewidth=1.5, transform=ax_dz.transAxes)
                ax_dz.text(8, 8, 'Skud i DZ', va='center', fontsize=9, transform=ax_dz.transAxes)
                
                fig_dz.subplots_adjust(bottom=0.05)
                st.pyplot(fig_dz)

            # TABEL
            stats_list = []
            for spiller in spiller_liste_dz:
                s_data = df_skud[df_skud['PLAYER_NAME'] == spiller]
                s_dz = s_data[s_data['IS_DZ_GEO']]
                efternavn = spiller.split()[-1] if isinstance(spiller, str) else spiller
                stats_list.append({
                    "Navn": efternavn,
                    "Skud i DZ": len(s_dz),
                    "Mål i DZ": len(s_dz[s_dz['EVENT_TYPEID'] == 16]),
                    "DZ %": (len(s_dz)/len(s_data)*100) if len(s_data) > 0 else 0
                })
            
            df_table_data = pd.DataFrame(stats_list).sort_values("Skud i DZ", ascending=False)
            
            fig_tab, ax_tab = plt.subplots(figsize=(12, 2.2)) 
            ax_tab.axis('off')
            
            the_table = ax_tab.table(
                cellText=[[int(v) for v in df_table_data['Skud i DZ'].values],
                          [int(v) for v in df_table_data['Mål i DZ'].values],
                          [f"{v:.1f}%" for v in df_table_data['DZ %'].values]],
                rowLabels=["Skud i DZ", "Mål i DZ", "DZ %"],
                colLabels=df_table_data['Navn'].values,
                loc='top', 
                cellLoc='center'
            )
            
            the_table.auto_set_font_size(False)
            the_table.set_fontsize(7.3)
            the_table.scale(1.0, 1.8)
            
            for (row, col), cell in the_table.get_celld().items():
                if row == 0 and col >= 0:
                    cell.get_text().set_rotation(270)
                    cell.get_text().set_va('center')
                    cell.set_height(0.35)
                elif col == -1:
                    cell.set_facecolor('#f2f2f2')
                    cell.get_text().set_weight('bold')

            fig_tab.subplots_adjust(top=0.85, bottom=0, left=0.1, right=0.9)
            st.pyplot(fig_tab)

    # --- TAB 3: ASSISTS ---
    with tab3:
        if df_assists.empty:
            st.warning("⚠️ Ingen assists fundet.")
        else:
            col_viz_a, col_ctrl_a = st.columns([3, 1])
            with col_ctrl_a:
                spiller_liste_a = sorted([s for s in df_assists['ASSIST_PLAYER'].unique() if pd.notna(s)])
                v_a = st.selectbox("Vælg spiller (Assists)", options=["Hvidovre IF"] + spiller_liste_a, key="sb_assist")
                df_a_vis = df_assists if v_a == "Hvidovre IF" else df_assists[df_assists['ASSIST_PLAYER'] == v_a]
                st.markdown(f'<div class="stat-box"><div class="stat-label">Goal Assists</div><div class="stat-value">{len(df_a_vis)}</div></div>', unsafe_allow_html=True)

            with col_viz_a:
                pitch_a = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig_a, ax_a = pitch_a.draw(figsize=(8, 10))
                if not df_a_vis.empty:
                    pitch_a.arrows(df_a_vis['PASS_START_X'], df_a_vis['PASS_START_Y'], 
                                   df_a_vis['SHOT_X'], df_a_vis['SHOT_Y'], 
                                   color='#888888', alpha=0.5, width=2, headwidth=4, ax=ax_a, zorder=1)
                    pitch_a.scatter(df_a_vis['PASS_START_X'], df_a_vis['PASS_START_Y'], 
                                    s=120, color=HIF_GOLD, edgecolors='black', linewidth=1, ax=ax_a, zorder=2)
                st.pyplot(fig_a)
