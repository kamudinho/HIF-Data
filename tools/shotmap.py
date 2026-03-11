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
    # --- CSS STYLING ---
    st.markdown("""
        <style>
            .stat-box { background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid #cc0000; margin-bottom: 10px; }
            .stat-label { font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }
            .stat-value { font-size: 1.5rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }
            .legend-dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; vertical-align: middle; }
        </style>
    """, unsafe_allow_html=True)
    
    df_skud = dp.get('playerstats', pd.DataFrame()).copy()
    if df_skud.empty:
        st.info("Ingen data fundet.")
        return

    # --- 1. ZONE DEFINITIONER ---
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

    tabs = st.tabs(["SPILLER", "SKUD", "DZ", "ZONER (S)", "ZONER (M)"])

    # --- TAB 1: SPILLEROVERSIGT ---
    with tabs[0]:
        stats = []
        for p in sorted(df_skud['PLAYER_NAME'].unique()):
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            dz = d[d['IS_DZ_GEO']]
            s, m = len(d), len(d[d['EVENT_TYPEID'] == 16])
            dzs, dzm = len(dz), len(dz[dz['EVENT_TYPEID'] == 16])
            stats.append({
                "Spiller": p.split()[-1], "S": s, "M": m, "Konv%": (m/s*100),
                "DZ-S": dzs, "DZ-M": dzm, "DZ%": (dzm/dzs*100) if dzs > 0 else 0,
                "DZ-Andel": (dzs/s*100)
            })
        df_f = pd.DataFrame(stats).sort_values("S", ascending=False)
        st.dataframe(df_f, use_container_width=True, height=(len(df_f) + 1) * 36, hide_index=True,
            column_config={
                "Konv%": st.column_config.NumberColumn("Konv%", format="%.1f%%"),
                "DZ%": st.column_config.NumberColumn("DZ-Konv%", format="%.1f%%"),
                "DZ-Andel": st.column_config.ProgressColumn("DZ-Andel", format="%.0f%%", min_value=0, max_value=100)
            })

    # --- TAB 2: AFSLUTNINGER (Rettet Konvertering) ---
    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            sel_p = st.selectbox("Vælg spiller", ["Hvidovre IF"] + sorted(df_skud['PLAYER_NAME'].unique()))
            d_v = df_skud if sel_p == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == sel_p]
            s_cnt, m_cnt = len(d_v), len(d_v[d_v["EVENT_TYPEID"]==16])
            konv = (m_cnt/s_cnt*100) if s_cnt > 0 else 0
            
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background:white; border:2px solid {HIF_RED};"></span>Skud</div><div class="stat-value">{s_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background:{HIF_RED};"></span>Mål</div><div class="stat-value">{m_cnt}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_GOLD}"><div class="stat-label">Konvertering</div><div class="stat-value">{konv:.2f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=80, c=colors, edgecolors=HIF_RED, linewidth=1, ax=ax)
            st.pyplot(fig)

    # --- TAB 3: DZ (Rettet med cirkler) ---
    with tabs[2]:
        c1, c2 = st.columns([2, 1])
        with c2:
            sel_dz = st.selectbox("Vælg spiller (DZ)", ["Hvidovre IF"] + sorted(df_skud['PLAYER_NAME'].unique()), key="dz_sel")
            d_v = df_skud if sel_dz == "Hvidovre IF" else df_skud[df_skud['PLAYER_NAME'] == sel_dz]
            dz_d = d_v[d_v['IS_DZ_GEO']]
            m_alt = len(d_v[d_v["EVENT_TYPEID"]==16])
            m_dz = len(dz_d[dz_d["EVENT_TYPEID"]==16])
            
            st.markdown(f'<div class="stat-box" style="border-left-color:{DZ_COLOR}"><div class="stat-label"><span class="legend-dot" style="background:white; border:2px solid {DZ_COLOR};"></span>DZ Skud</div><div class="stat-value">{len(dz_d)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="legend-dot" style="background:{HIF_RED};"></span>DZ Mål</div><div class="stat-value">{m_dz}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color:{HIF_GOLD}"><div class="stat-label">Andel af mål fra DZ</div><div class="stat-value">{(m_dz/m_alt*100 if m_alt>0 else 0):.1f}%</div></div>', unsafe_allow_html=True)
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            ax.add_patch(patches.Rectangle((37, 88.5), 26, 11.5, color=DZ_COLOR, alpha=0.15))
            colors = (dz_d['EVENT_TYPEID'] == 16).map({True: HIF_RED, False: 'white'})
            pitch.scatter(dz_d['EVENT_X'], dz_d['EVENT_Y'], s=80, c=colors, edgecolors=HIF_RED, ax=ax)
            st.pyplot(fig)

    # --- TAB 4 & 5: ZONER (Filtreret Zone 8) ---
    def zone_plot(data, is_m):
        c1, c2 = st.columns([2, 1])
        z_map = {}
        for z in ZONE_BOUNDARIES.keys():
            zd = data[data['Zone'] == z]
            cnt = len(zd)
            top = zd['PLAYER_NAME'].mode().iloc[0].split()[-1] if cnt > 0 else "-"
            z_map[z] = (cnt, top)
        
        with c2:
            st.write(f"**{'Mål' if is_m else 'Skud'} pr. Zone**")
            # Fjerner Zone 8 fra tabellen så den ikke fylder
            df_zone_vis = pd.DataFrame([{"Zone": k, "Antal": v[0]} for k, v in z_map.items() if v[0] > 0 and k != "Zone 8"])
            st.dataframe(df_zone_vis, hide_index=True)
        
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw()
            ax.set_ylim(55, 105) # Fokus på angrebszoner
            max_val = max([v[0] for k, v in z_map.items() if k != "Zone 8"]) if not df_zone_vis.empty else 1
            cmap = plt.cm.YlOrRd if is_m else plt.cm.Blues
            
            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] < 70: continue
                val, top = z_map[name]
                rect = patches.Rectangle((b["x_min"], b["y_min"]), b["x_max"]-b["x_min"], b["y_max"]-b["y_min"], 
                                         facecolor=cmap(val/max_val) if val > 0 else '#f9f9f9', alpha=0.6, edgecolor='black', linestyle='--')
                ax.add_patch(rect)
                if val > 0:
                    ax.text(b["x_min"]+(b["x_max"]-b["x_min"])/2, b["y_min"]+(b["y_max"]-b["y_min"])/2, 
                            f"{name.replace('Zone ', 'Z')}\n{val}\n{top}", ha='center', va='center', fontsize=7, fontweight='bold')
            st.pyplot(fig)

    with tabs[3]: zone_plot(df_skud, False)
    with tabs[4]: zone_plot(df_skud[df_skud['EVENT_TYPEID'] == 16], True)
