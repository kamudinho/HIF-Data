import streamlit as st
import pandas as pd
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- KONSTANTER (Beholdes for konsistens) ---
HIF_RED = '#cc0000'
ASSIST_BLUE = '#1e90ff'
HIF_UUID = '8gxd9ry2580pu1b1dd5ny9ymy'

OPTA_MAP_DK = {
    1: "Aflevering", 2: "Aflevering", 3: "Dribling", 4: "Tackling", 
    5: "Frispark", 6: "Hjørnespark", 7: "Tackling", 8: "Interception",
    10: "Redning", 12: "Skud", 13: "Skud", 14: "Skud", 15: "Skud", 
    16: "MÅL", 43: "Frispark", 44: "Indkast", 49: "Opsamling", 50: "Opsnapning",
    107: "Restart"
}

def vis_side(dp):
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 10px; }
            .stat-label { font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }
            .stat-value { font-size: 1.5rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }
            .legend-dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; vertical-align: middle; }
        </style>
    """, unsafe_allow_html=True)

    # Henter data
    df_raw = dp.get('playerstats', pd.DataFrame()).copy()
    
    if df_raw.empty:
        st.info("Ingen data fundet i 'playerstats'.")
        return

    # --- 1. HOLDVALG ---
    if 'TEAM_NAME' in df_raw.columns:
        hold_liste = sorted(df_raw['TEAM_NAME'].unique())
        valgt_hold = st.selectbox("Vælg Hold", hold_liste)
        df_skud = df_raw[df_raw['TEAM_NAME'] == valgt_hold].copy()
    else:
        df_skud = df_raw.copy()

    # --- 2. ZONE DEFINITIONER ---
    P_L, P_W = 105.0, 68.0
    X_MID_L, X_MID_R = (P_W - 18.32) / 2, (P_W + 18.32) / 2
    X_INN_L, X_INN_R = (P_W - 40.2) / 2, (P_W + 40.2) / 2
    Y_GOAL, Y_6YD, Y_PK, Y_18YD, Y_MID = 105.0, 99.5, 94.0, 88.5, 75.0

    ZONE_BOUNDARIES = {
        "Zone 1": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 2": {"y_min": Y_PK, "y_max": Y_6YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 3": {"y_min": Y_18YD, "y_max": Y_PK, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 4A": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_MID_R, "x_max": X_INN_R},
        "Zone 4B": {"y_min": Y_6YD, "y_max": Y_GOAL, "x_min": X_INN_L, "x_max": X_MID_L},
        "Zone 5A": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_MID_R, "x_max": X_INN_R},
        "Zone 5B": {"y_min": Y_18YD, "y_max": Y_6YD, "x_min": X_INN_L, "x_max": X_MID_L},
        "Zone 6A": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": X_INN_R, "x_max": P_W},
        "Zone 6B": {"y_min": Y_18YD, "y_max": Y_GOAL, "x_min": 0, "x_max": X_INN_L},
        "Zone 7C": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": 0, "x_max": X_MID_L},
        "Zone 7B": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_L, "x_max": X_MID_R},
        "Zone 7A": {"y_min": Y_MID, "y_max": Y_18YD, "x_min": X_MID_R, "x_max": P_W},
        "Zone 8":  {"y_min": 0, "y_max": Y_MID, "x_min": 0, "x_max": P_W}
    }

    def map_to_zone(r):
        mx, my = r['EVENT_X'] * (P_L / 100), r['EVENT_Y'] * (P_W / 100)
        for z, b in ZONE_BOUNDARIES.items():
            if b["y_min"] <= mx <= b["y_max"] and b["x_min"] <= my <= b["x_max"]:
                return z
        return "Zone 8"

    df_skud['Zone'] = df_skud.apply(map_to_zone, axis=1)
    df_skud['IS_DZ_GEO'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)

    tabs = st.tabs(["SPILLEROVERSIGT", "AFSLUTNINGER", "DZ-AFSLUTNINGER", "AFSLUTNINGSZONER", "MÅLZONER", "SEKVENSER"])

    # --- TAB 1: SPILLEROVERSIGT ---
    with tabs[0]:
        stats = []
        for p in sorted(df_skud['PLAYER_NAME'].unique()):
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            dz = d[d['IS_DZ_GEO']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            dzs, dzm = len(dz), len(dz[dz['EVENT_TYPEID'] == 16])
            stats.append({
                "Spiller": p.split()[-1], 
                "Skud": s, "Mål": m, 
                "Konvertering%": (m/s*100) if s > 0 else 0,
                "DZ-Skud": dzs, "DZ-Mål": dzm, 
                "DZ-Konvertering%": (dzm/dzs*100) if dzs > 0 else 0,
                "DZ-Andel": (dzs/s*100) if s > 0 else 0
            })
        df_f = pd.DataFrame(stats).sort_values("Skud", ascending=False)
        st.dataframe(df_f, use_container_width=True, height=(len(df_f)+1)*36, hide_index=True,
                    column_config={
                        "Konvertering%": st.column_config.NumberColumn("Konvertering%", format="%.1f%%"),
                        "DZ-Konvertering%": st.column_config.NumberColumn("DZ-Konvertering%", format="%.1f%%"),
                        "DZ-Andel": st.column_config.ProgressColumn("DZ-Andel", format="%.0f%%", min_value=0, max_value=100)
                    })

    # --- TAB 2: AFSLUTNINGER ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            sel_p = st.selectbox("Vælg spiller", ["Hele Holdet"] + sorted(df_skud['PLAYER_NAME'].unique()))
            d_v = df_skud if sel_p == "Hele Holdet" else df_skud[df_skud['PLAYER_NAME'] == sel_p]
            s_cnt, m_cnt = len(d_v), len(d_v[d_v["EVENT_TYPEID"]==16])
            konv = (m_cnt/s_cnt*100) if s_cnt > 0 else 0
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{s_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{m_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_GOLD}"><div class="stat-label">Konvertering</div><div class="stat-value">{konv:.2f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=20, c=colors, edgecolors=HIF_RED, linewidth=1, ax=ax)
            st.pyplot(fig)

    # --- TAB 3: DZ ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2:
            sel_dz = st.selectbox("Vælg spiller (DZ)", ["Hele Holdet"] + sorted(df_skud['PLAYER_NAME'].unique()), key="dz_sel")
            d_v = df_skud if sel_dz == "Hele Holdet" else df_skud[df_skud['PLAYER_NAME'] == sel_dz]
            dz_d = d_v[d_v['IS_DZ_GEO']]
            m_dz = len(dz_d[dz_d["EVENT_TYPEID"]==16])
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Skud</div><div class="stat-value">{len(dz_d)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">DZ Mål</div><div class="stat-value">{m_dz}</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            colors = (dz_d['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=20, c=colors, edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- ZONER FUNKTION ---
    def zone_plot_enhanced(data, is_m):
        col_viz, col_ctrl = st.columns([1.8, 1])
        total_count = len(data)
        zone_stats = {}
        for zone, b in ZONE_BOUNDARIES.items():
            z_data = data[data['Zone'] == zone]
            cnt = len(z_data)
            top_p = z_data['PLAYER_NAME'].mode().iloc[0].split()[-1] if cnt > 0 else "-"
            zone_stats[zone] = {'cnt': cnt, 'pct': (cnt/total_count*100) if total_count>0 else 0, 'top': top_p}

        with col_ctrl:
            label = "Mål" if is_m else "Skud"
            z_df = pd.DataFrame([{'Zone': k, label: v['cnt'], 'Top': v['top']} for k, v in zone_stats.items() if v['cnt'] > 0 and k != "Zone 8"]).sort_values(label, ascending=False)
            st.dataframe(z_df, hide_index=True, use_container_width=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            max_v = max([v['cnt'] for k, v in zone_stats.items() if k != "Zone 8"]) if total_count > 0 else 1
            cmap = plt.cm.YlOrRd if is_m else plt.cm.Blues
            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                y_min_draw = max(b["y_min"], 55)
                stats = zone_stats[name]
                face = cmap(stats['cnt']/max_v) if stats['cnt'] > 0 else '#f9f9f9'
                ax.add_patch(patches.Rectangle((b["x_min"], y_min_draw), b["x_max"]-b["x_min"], b["y_max"]-y_min_draw, facecolor=face, alpha=0.7, edgecolor='black', ls='--'))
                if stats['cnt'] > 0:
                    ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, y_min_draw+(b["y_max"]-y_min_draw)/2, f"{stats['cnt']}", ha='center', va='center', fontsize=8, fontweight='bold')
            st.pyplot(fig)

    with tabs[3]: zone_plot_enhanced(df_skud, False)
    with tabs[4]: zone_plot_enhanced(df_skud[df_skud['EVENT_TYPEID'] == 16], True)
    with tabs[5]:
        # --- CSS TIL OPTIMERING AF LAYOUT ---
        st.markdown(f"""
            <style>
                .stat-box-side {{ background-color: #f8f9fa; padding: 8px 12px; border-radius: 5px; border-left: 5px solid {HIF_RED}; margin-bottom: 6px; }}
                .dot {{ height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }}
                .play-flow-container {{ background: #ffffff; padding: 12px; border-radius: 8px; border: 1px solid #eee; margin-top: 5px; }}
                .flow-step {{ font-weight: 700; color: #333; font-size: 0.85rem; }}
                .flow-action {{ color: #666; font-size: 0.75rem; font-weight: 400; }}
                .flow-arrow {{ color: {HIF_RED}; margin: 0 4px; font-weight: bold; }}
            </style>
        """, unsafe_allow_html=True)

        df_raw = dp.get('opta', {}).get('opta_sequence_map', pd.DataFrame())
        if df_raw.empty:
            st.info("Ingen sekvens-data fundet for denne kamp.")
            return

        # Data-forberedelse
        df = df_raw.copy()
        df.columns = [c.upper() for c in df.columns]
        col_x = 'RAW_X' if 'RAW_X' in df.columns else 'EVENT_X'
        col_y = 'RAW_Y' if 'RAW_Y' in df.columns else 'EVENT_Y'

        df['EVENT_CONTESTANT_OPTAUUID'] = df['EVENT_CONTESTANT_OPTAUUID'].astype(str).str.lower()
        local_hif_uuid = HIF_UUID.lower()
        
        goals = df[df['EVENT_TYPEID'] == 16].sort_values('EVENT_TIMESTAMP', ascending=False)
        if goals.empty:
            st.warning("Ingen mål fundet i sekvens-data.")
            return

        goals['LABEL'] = goals.apply(lambda x: f"{x['EVENT_TIMEMIN']}'. min: {x['PLAYER_NAME']}", axis=1)
        
        col_main, col_side = st.columns([2.5, 1])

        with col_side:
            sel_label = st.selectbox("Vælg mål", options=goals['LABEL'].unique(), label_visibility="collapsed")
            sel_row = goals[goals['LABEL'] == sel_label].iloc[0]
            
            hif_seq = df[(df['SEQUENCEID'] == sel_row['SEQUENCEID']) & (df['EVENT_CONTESTANT_OPTAUUID'] == local_hif_uuid)].copy()
            hif_seq = hif_seq.sort_values('EVENT_TIMESTAMP').reset_index(drop=True)

            if not hif_seq.empty:
                scorer = hif_seq.iloc[-1]['PLAYER_NAME'].split()[-1] if pd.notnull(hif_seq.iloc[-1]['PLAYER_NAME']) else "HIF"
                assist = hif_seq.iloc[-2]['PLAYER_NAME'].split()[-1] if len(hif_seq) > 1 else "Solo"
                
                st.markdown(f'<div class="stat-box-side"><span class="dot" style="background-color:{HIF_RED}"></span><b>Mål:</b> {scorer}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-box-side" style="border-left-color:{ASSIST_BLUE}"><span class="dot" style="background-color:{ASSIST_BLUE}"></span><b>Assist:</b> {assist}</div>', unsafe_allow_html=True)

                st.caption("Deltagere i sekvensen")
                hif_seq['Spiller'] = hif_seq['PLAYER_NAME'].apply(lambda x: x.split()[-1] if pd.notnull(x) else "HIF")
                st.table(hif_seq['Spiller'].value_counts().reset_index().rename(columns={'index': 'Spiller', 'Spiller': 'Aktioner'}))

        with col_main:
            pitch = Pitch(pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(9, 6))
            flip = True if sel_row[col_x] < 50 else False
            
            prev = None
            for i, r in hif_seq.iterrows():
                cx, cy = (100 - r[col_x] if flip else r[col_x]), (100 - r[col_y] if flip else r[col_y])
                if prev:
                    ax.annotate('', xy=(cx, cy), xytext=(prev[0], prev[1]),
                                arrowprops=dict(arrowstyle='->', color='#ccc', lw=1.5, alpha=0.4, shrinkA=5, shrinkB=5))
                
                p_name = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else ""
                dot_col = HIF_RED if r['EVENT_TYPEID'] == 16 else (ASSIST_BLUE if p_name == assist else '#aaaaaa')
                pitch.scatter(cx, cy, s=180, color=dot_col, edgecolors='white', ax=ax, zorder=5)
                ax.text(cx, cy + 2.5, p_name, fontsize=8, ha='center', fontweight='bold')
                prev = (cx, cy)
            
            st.pyplot(fig, bbox_inches='tight', pad_inches=0)

            # Sekvens-oversigt tekst-flow
            steps = []
            for _, r in hif_seq.iterrows():
                p = r['PLAYER_NAME'].split()[-1] if pd.notnull(r['PLAYER_NAME']) else "HIF"
                tid = int(r['EVENT_TYPEID'])
                h = OPTA_MAP_DK.get(tid, f"Aktion {tid}")
                if tid == 16: h = "MÅL"
                steps.append(f'<span class="flow-step">{p}</span> <span class="flow-action">({h})</span>')
            
            flow_string = ' <span class="flow-arrow">→</span> '.join(steps)
            st.markdown(f'<div class="play-flow-container">{flow_string}</div>', unsafe_allow_html=True)
