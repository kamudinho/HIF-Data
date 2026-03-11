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

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER"])

    # Fælles indstilling for prikstørrelse
    DOT_SIZE = 90 
    LINE_WIDTH = 1.2

    # --- TAB 1: SHOT-STATISTIK ---
    with tab1:
        if df_skud.empty:
            st.info("Ingen data fundet til statistik.")
        else:
            
            stats_list = []
            spiller_liste_dz = sorted(df_skud['PLAYER_NAME'].unique())
            
            for spiller in spiller_liste_dz:
                s_data = df_skud[df_skud['PLAYER_NAME'] == spiller]
                s_dz = s_data[s_data['IS_DZ_GEO']]
                
                # Grunddata
                total_skud = len(s_data)
                skud_dz = len(s_dz)
                total_maal = len(s_data[s_data['EVENT_TYPEID'] == 16])
                maal_dz = len(s_dz[s_dz['EVENT_TYPEID'] == 16])
                
                # Beregninger (sikret mod division med nul)
                dz_andel = (skud_dz / total_skud * 100) if total_skud > 0 else 0
                konv_total = (total_maal / total_skud * 100) if total_skud > 0 else 0
                konv_dz = (maal_dz / skud_dz * 100) if skud_dz > 0 else 0
                
                if total_skud > 0:
                    efternavn = spiller.split()[-1] if isinstance(spiller, str) else spiller
                    stats_list.append({
                        "Spiller": efternavn, 
                        "Skud": int(total_skud),
                        "Mål": int(total_maal),
                        "Konv. %": konv_total,
                        "Skud i DZ": int(skud_dz),
                        "Mål i DZ": int(maal_dz),
                        "DZ Konv. %": konv_dz,
                        "DZ Andel": dz_andel
                    })
            
            if stats_list:
                df_table = pd.DataFrame(stats_list).sort_values("Skud i DZ", ascending=False)
                
                # Beregn højde så hele tabellen vises (ca. 35px pr række + header)
                table_height = (len(df_table) + 1) * 35 + 2

                st.dataframe(
                    df_table,
                    column_config={
                        "Spiller": st.column_config.TextColumn("Spiller", width="medium"),
                        "Skud": st.column_config.NumberColumn("Skud", format="%d"),
                        "Mål": st.column_config.NumberColumn("Mål", format="%d"),
                        "Konv. %": st.column_config.NumberColumn("Konv. %", format="%.1f%%", help="Generel konverteringsrate"),
                        "Skud i DZ": st.column_config.NumberColumn("Skud DZ", format="%d"),
                        "Mål i DZ": st.column_config.NumberColumn("Mål DZ", format="%d"),
                        "DZ Konv. %": st.column_config.NumberColumn("DZ Konv. %", format="%.1f%%", help="Konverteringsrate inde i Danger Zone"),
                        "DZ Andel": st.column_config.ProgressColumn(
                            "DZ Andel %", 
                            help="Hvor stor en del af spillerens skud er i DZ?",
                            format="%.1f%%",
                            min_value=0,
                            max_value=100
                        )
                    },
                    hide_index=True,
                    height=table_height,
                    use_container_width=True
                )

    # --- TAB 2: AFSLUTNINGER ---
    with tab2:
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

    # --- TAB 3: DANGER ZONE ---
    with tab3:
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
                    <div class="stat-box" style="border-left-color: {DZ_COLOR}"><div class="stat-label">Skud i DZ</div><div class="stat-value">{len(dz_hits)}</div></div>
                    <div class="stat-box" style="border-left-color: {HIF_RED}"><div class="stat-label">Mål i DZ</div><div class="stat-value">{dz_goals}</div></div>
                    <div class="stat-box" style="border-left-color: #333;"><div class="stat-label">HIF i DZ</div><div class="stat-value">{hif_dz_pct:.1f}%</div></div>
                """, unsafe_allow_html=True)

            with col_dz_viz:
                pitch_dz = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
                fig_dz, ax_dz = pitch_dz.draw(figsize=(6, 8)) 
                ax_dz.set_ylim(70, 102) 
                
                # Danger Zone rektangel
                dz_rect = patches.Rectangle((37, 88.5), 26, 11.5, linewidth=1.5, edgecolor=DZ_COLOR, facecolor=DZ_COLOR, alpha=0.1, linestyle='--', zorder=1)
                ax_dz.add_patch(dz_rect)
                
                if not dz_hits.empty:
                    c_dz = (dz_hits['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
                    pitch_dz.scatter(dz_hits['EVENT_X'], dz_hits['EVENT_Y'], s=DOT_SIZE, c=c_dz, edgecolors=HIF_RED, linewidth=LINE_WIDTH, ax=ax_dz, zorder=2)
                
                st.pyplot(fig_dz)

    # --- TAB 4: AFSLUTNINGSZONER (NY) ---
    with tab4:
        if df_skud.empty:
            st.info("Ingen data fundet.")
        else:
            col_z_viz, col_z_ctrl = st.columns([2.2, 1])
            
            # 1. Definer zoner (Præcis som dit assist-script)
            PITCH_L, PITCH_W = 105, 68
            C_MIN, C_MAX = (PITCH_W - 18.32)/2, (PITCH_W + 18.32)/2
            W_INNER_MIN, W_INNER_MAX = (PITCH_W - 40.2)/2, (PITCH_W + 40.2)/2

            ZONE_BOUNDS = {
                "Zone 1": {"y": (99.5, 105.0), "x": (C_MIN, C_MAX)},
                "Zone 2": {"y": (94.0, 99.5),  "x": (C_MIN, C_MAX)},
                "Zone 3": {"y": (88.5, 94.0),  "x": (C_MIN, C_MAX)},
                "Zone 4A": {"y": (99.5, 105.0), "x": (C_MAX, W_INNER_MAX)},
                "Zone 4B": {"y": (99.5, 105.0), "x": (W_INNER_MIN, C_MIN)},
                "Zone 5A": {"y": (88.5, 99.5),  "x": (C_MAX, W_INNER_MAX)},
                "Zone 5B": {"y": (88.5, 99.5),  "x": (W_INNER_MIN, C_MIN)},
                "Zone 6A": {"y": (88.5, 105.0), "x": (W_INNER_MAX, PITCH_W)},
                "Zone 6B": {"y": (88.5, 105.0), "x": (0, W_INNER_MIN)},
                "Zone 7B": {"y": (75.0, 88.5),  "x": (C_MIN, C_MAX)},
                "Zone 7C": {"y": (75.0, 88.5),  "x": (0, C_MIN)},
                "Zone 7A": {"y": (75.0, 88.5),  "x": (C_MAX, PITCH_W)},
                "Zone 8":  {"y": (0, 75.0),     "x": (0, PITCH_W)}
            }

            def map_shot_to_zone(r):
                # Opta Y er bredde (0-100), Opta X er længde (0-100)
                xm, ym = r['EVENT_Y'] * (PITCH_W/100), r['EVENT_X'] * (PITCH_L/100)
                for z, b in ZONE_BOUNDS.items():
                    if b["y"][0] <= ym <= b["y"][1] and b["x"][0] <= xm <= b["x"][1]:
                        return z
                return "Zone 8"

            df_skud['Zone'] = df_skud.apply(map_shot_to_zone, axis=1)
            df_goals_only = df_skud[df_skud['EVENT_TYPEID'] == 16].copy()
            total_goals = len(df_goals_only)

            # Beregn stats pr. zone
            zone_stats = {}
            for zone in ZONE_BOUNDS.keys():
                z_data = df_goals_only[df_goals_only['Zone'] == zone]
                count = len(z_data)
                pct = (count / total_goals * 100) if total_goals > 0 else 0
                top_p = z_data['PLAYER_NAME'].mode().iloc[0] if not z_data.empty else "-"
                short_p = top_p.split(' ')[-1] if top_p != "-" else "-"
                zone_stats[zone] = {'count': count, 'pct': pct, 'top': top_p, 'short': short_p}

            with col_z_ctrl:
                st.markdown("**MÅL PR. ZONE**")
                z_df = pd.DataFrame([
                    {'Zone': k, 'Mål': v['count'], 'Pct': f"{v['pct']:.1f}%", 'Top Skytte': v['top']}
                    for k, v in zone_stats.items() if v['count'] > 0
                ]).sort_values('Mål', ascending=False)
                st.dataframe(z_df, hide_index=True, use_container_width=True)

            with col_z_viz:
                pitch_z = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
                fig_z, ax_z = pitch_z.draw(figsize=(8, 10))
                ax_z.set_ylim(50, 105) # Fokus på angrebshalvdel

                max_goals = max([v['count'] for v in zone_stats.values()]) if total_goals > 0 else 1
                cmap = plt.cm.YlOrRd 

                for name, b in ZONE_BOUNDS.items():
                    if b["y"][1] <= 50: continue
                    y_min_plot = max(b["y"][0], 50)
                    rect_h = b["y"][1] - y_min_plot
                    
                    s = zone_stats[name]
                    color_val = s['count'] / max_goals
                    face_color = cmap(color_val) if s['count'] > 0 else '#f9f9f9'
                    
                    rect = patches.Rectangle((b["x"][0], y_min_plot), b["x"][1]-b["x"][0], rect_h,
                                     edgecolor='black', linestyle='--', facecolor=face_color, alpha=0.7)
                    ax_z.add_patch(rect)

                    # Tekst i zone (Z-navn, Antal, Navn)
                    z_text = f"$\\mathbf{{{name.replace('Zone ', 'Z')}}}$\n{s['count']} ({s['pct']:.0f}%)\n{s['short']}"
                    ax_z.text(b["x"][0] + (b["x"][1]-b["x"][0])/2, y_min_plot + rect_h/2, 
                              z_text, ha='center', va='center', fontsize=7,
                              color='black' if color_val < 0.6 else 'white')

                st.pyplot(fig_z)

    # --- TAB 5: MÅLZONER (Hvor målene scores fra) ---
    with tab5:
        df_goals_only = df_skud[df_skud['EVENT_TYPEID'] == 16].copy()
        
        if df_goals_only.empty:
            st.info("Ingen scoringer fundet i data.")
        else:
            col_m_viz, col_m_ctrl = st.columns([2.2, 1])
            
            # 1. Genbrug Zone-logik (Meter -> Opta)
            PITCH_L, PITCH_W = 105, 68
            C_MIN, C_MAX = (PITCH_W - 18.32)/2, (PITCH_W + 18.32)/2
            W_INNER_MIN, W_INNER_MAX = (PITCH_W - 40.2)/2, (PITCH_W + 40.2)/2

            ZONE_BOUNDS = {
                "Zone 1": {"y": (99.5, 105.0), "x": (C_MIN, C_MAX)},
                "Zone 2": {"y": (94.0, 99.5),  "x": (C_MIN, C_MAX)},
                "Zone 3": {"y": (88.5, 94.0),  "x": (C_MIN, C_MAX)},
                "Zone 4A": {"y": (99.5, 105.0), "x": (C_MAX, W_INNER_MAX)},
                "Zone 4B": {"y": (99.5, 105.0), "x": (W_INNER_MIN, C_MIN)},
                "Zone 5A": {"y": (88.5, 99.5),  "x": (C_MAX, W_INNER_MAX)},
                "Zone 5B": {"y": (88.5, 99.5),  "x": (W_INNER_MIN, C_MIN)},
                "Zone 6A": {"y": (88.5, 105.0), "x": (W_INNER_MAX, PITCH_W)},
                "Zone 6B": {"y": (88.5, 105.0), "x": (0, W_INNER_MIN)},
                "Zone 7B": {"y": (75.0, 88.5),  "x": (C_MIN, C_MAX)},
                "Zone 7C": {"y": (75.0, 88.5),  "x": (0, C_MIN)},
                "Zone 7A": {"y": (75.0, 88.5),  "x": (C_MAX, PITCH_W)},
                "Zone 8":  {"y": (0, 75.0),     "x": (0, PITCH_W)}
            }

            def map_goal_zone(r):
                xm, ym = r['EVENT_Y'] * (PITCH_W/100), r['EVENT_X'] * (PITCH_L/100)
                for z, b in ZONE_BOUNDS.items():
                    if b["y"][0] <= ym <= b["y"][1] and b["x"][0] <= xm <= b["x"][1]:
                        return z
                return "Zone 8"

            df_goals_only['Zone'] = df_goals_only.apply(map_goal_zone, axis=1)
            total_mål = len(df_goals_only)

            # Beregn zone-statistik
            mål_zone_stats = {}
            for zone in ZONE_BOUNDS.keys():
                z_data = df_goals_only[df_goals_only['Zone'] == zone]
                count = len(z_data)
                pct = (count / total_mål * 100) if total_mål > 0 else 0
                top_scorer = z_data['PLAYER_NAME'].mode().iloc[0] if not z_data.empty else "-"
                short_name = top_scorer.split(' ')[-1] if top_scorer != "-" else "-"
                mål_zone_stats[zone] = {'count': count, 'pct': pct, 'top': top_scorer, 'short': short_name}

            with col_m_ctrl:
                st.markdown("**MÅL-OVERSIGT PR. ZONE**")
                m_df = pd.DataFrame([
                    {'Zone': k, 'Mål': v['count'], 'Pct': f"{v['pct']:.1f}%", 'Topscorer': v['top']}
                    for k, v in mål_zone_stats.items() if v['count'] > 0
                ]).sort_values('Mål', ascending=False)
                
                st.dataframe(m_df, hide_index=True, use_container_width=True)
                st.info(f"Hvidovre har scoret {total_mål} mål i denne periode.")

            with col_m_viz:
                pitch_m = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
                fig_m, ax_m = pitch_m.draw(figsize=(8, 10))
                ax_m.set_ylim(50, 105)

                max_mål = max([v['count'] for v in mål_zone_stats.values()]) if total_mål > 0 else 1
                cmap = plt.cm.YlOrRd 

                for name, b in ZONE_BOUNDS.items():
                    if b["y"][1] <= 50: continue
                    y_min_p = max(b["y"][0], 50)
                    rect_h = b["y"][1] - y_min_p
                    
                    s = mål_zone_stats[name]
                    color_val = s['count'] / max_mål
                    # Vi bruger en rød-gylden skala til mål
                    face_color = cmap(color_val) if s['count'] > 0 else '#f9f9f9'
                    
                    rect = patches.Rectangle((b["x"][0], y_min_p), b["x"][1]-b["x"][0], rect_h,
                                     edgecolor='black', linestyle='--', facecolor=face_color, alpha=0.8)
                    ax_m.add_patch(rect)

                    # Tekst i zonen: Navn, Antal, Topscorer
                    z_label = (f"$\\mathbf{{{name.replace('Zone ', 'Z')}}}$\n"
                               f"{s['count']} mål\n"
                               f"{s['short']}")
                    
                    ax_m.text(b["x"][0] + (b["x"][1]-b["x"][0])/2, y_min_p + rect_h/2, 
                              z_label, ha='center', va='center', fontsize=8,
                              color='black' if color_val < 0.6 else 'white')

                st.pyplot(fig_m)
