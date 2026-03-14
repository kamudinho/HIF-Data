import streamlit as st
import pandas as pd
import numpy as np
from mplsoccer import VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from data.utils.team_mapping import TEAMS

# Konstanter til farver
LIGA_BLUE = '#1f77b4'

def vis_side(dp):
    # --- DEBUG INFO ---
    opta_data = dp.get('opta', {})
    available_keys = list(opta_data.keys())
    
    # Hvis vi slet ikke kan finde 'league_shotevents'
    if 'league_shotevents' not in opta_data:
        st.error(f"Nøglen 'league_shotevents' mangler i opta-pakken. Fundne nøgler: {available_keys}")
        # Tjekker om den ligger i roden i stedet
        df_skud = dp.get('league_shotevents', pd.DataFrame())
    else:
        df_skud = opta_data.get('league_shotevents', pd.DataFrame())

    if df_skud.empty:
        st.warning("Dataframe fundet, men den er TOM. Dette skyldes ofte at SQL-queryen ikke finder matches i Snowflake.")
        return
    
    # Da SQL allerede har filtreret Hvidovre FRA, behøver vi ikke gøre det her.
    # Vi skal bare definere hvilken kolonne der holder hold-ID'et til oversigten
    col_team = 'EVENT_CONTESTANT_OPTAUUID'

    # --- 2. CSS STYLING ---
    st.markdown(f"""
        <style>
            .stat-box {{ background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 5px solid {LIGA_BLUE}; margin-bottom: 10px; }}
            .stat-label {{ font-size: 0.8rem; text-transform: uppercase; color: #666; font-weight: bold; }}
            .stat-value {{ font-size: 1.5rem; font-weight: 800; color: #1a1a1a; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 3. ZONE LOGIK ---
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

    df_skud['ZONE'] = df_skud.apply(map_to_zone, axis=1)

    # --- 4. TABS ---
    tabs = st.tabs(["LIGAPROFILER", "AFSLUTNINGER", "DZ-ANALYSE", "SKUDZONER", "MÅLZONER"])

    # --- 4. TABS ---
    tabs = st.tabs(["LIGAPROFILER", "AFSLUTNINGER", "DZ-ANALYSE", "SKUDZONER", "MÅLZONER"])

    with tabs[0]:
        stats = []
        uuid_to_name = {v['opta_uuid'].upper(): k for k, v in TEAMS.items() if v.get('opta_uuid')}
        
        # Saml al data først
        for p in df_skud['PLAYER_NAME'].unique():
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            t_uuid = str(d[col_team].iloc[0]).upper()
            t_name = uuid_to_name.get(t_uuid, "Modstander")
            
            s = len(d)
            m = len(d[d['EVENT_TYPEID'] == 16])
            xg_val = pd.to_numeric(d['XG_RAW'], errors='coerce').sum()
            
            if s > 0:
                stats.append({
                    "Spiller": p, 
                    "Hold": t_name, 
                    "Skud": int(s),
                    "Mål": int(m),
                    "Konv.%": float(round((m/s*100), 1)) if s > 0 else 0.0, 
                    "xG": float(round(xg_val, 2))
                })
        
        # Lav DF og vis den UDENFOR for-loopet
        df_stats = pd.DataFrame(stats).sort_values("Skud", ascending=False)
        
        st.dataframe(
            df_stats, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "xG": st.column_config.NumberColumn("xG", format="%.2f"),
                "Konv.%": st.column_config.NumberColumn("Konv.%", format="%.1f%%"),
                "Skud": st.column_config.NumberColumn("Skud", format="%d"),
                "Mål": st.column_config.NumberColumn("Mål", format="%d")
            }
        )
        
        if dz_stats:
            df_dz = pd.DataFrame(dz_stats).sort_values("DZ Skud", ascending=False)
            st.dataframe(df_dz, use_container_width=True, hide_index=True)
        else:
            st.write("Ingen DZ-data fundet.")

    with tabs[1]:
        c1, c2 = st.columns([2, 1])
        with c2:
            sel_p = st.selectbox("Vælg Spiller (Liga)", ["HELE LIGAEN"] + sorted(df_skud['PLAYER_NAME'].unique()))
            d_v = df_skud if sel_p == "HELE LIGAEN" else df_skud[df_skud['PLAYER_NAME'] == sel_p]
            
            st.markdown(f'<div class="stat-box"><div class="stat-label">Skud</div><div class="stat-value">{len(d_v)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box"><div class="stat-label">Mål</div><div class="stat-value">{len(d_v[d_v["EVENT_TYPEID"]==16])}</div></div>', unsafe_allow_html=True)
        
        with c1:
            pitch = VerticalPitch(half=True, pitch_type='opta', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(5, 7))
            # Mål er blå, missere er hvide med blå kant
            colors = (d_v['EVENT_TYPEID'] == 16).map({True: LIGA_BLUE, False: 'white'})
            pitch.scatter(d_v['EVENT_X'], d_v['EVENT_Y'], s=70, c=colors, edgecolors=LIGA_BLUE, ax=ax, alpha=0.6)
            st.pyplot(fig)

    with tabs[2]:
        st.subheader("Danger Zone (DZ) Analyse")
        st.info("Danger Zone er det centrale område i feltet (mellem målstolperne), hvorfra de fleste mål scores.")
        
        # Beregn DZ skud (defineret geografisk i din zone logik tidligere)
        # Vi genbruger din IS_DZ_GEO logik eller laver en hurtig filtrering:
        df_skud['IS_DZ'] = (df_skud['EVENT_X'] >= 88.5) & (df_skud['EVENT_Y'] >= 37.0) & (df_skud['EVENT_Y'] <= 63.0)
        
        dz_stats = []
        for p in df_skud['PLAYER_NAME'].unique():
            d = df_skud[df_skud['PLAYER_NAME'] == p]
            dz_d = d[d['IS_DZ'] == True]
            
            if len(dz_d) > 0:
                dz_stats.append({
                    "Spiller": p,
                    "DZ Skud": len(dz_d),
                    "DZ Mål": len(dz_d[dz_d['EVENT_TYPEID'] == 16]),
                    "DZ xG": pd.to_numeric(dz_d['XG_RAW'], errors='coerce').sum()
                })

    # --- 5. ZONE PLOTS FUNKTION ---
    def zone_viz(data, is_m):
        viz, ctrl = st.columns([1.8, 1])
        with ctrl:
            z_counts = data.groupby('ZONE').size().reset_index(name='Antal')
            z_counts = z_counts[z_counts['ZONE'] != 'Zone 8'].sort_values('Antal', ascending=False)
            st.write(f"**Top Zoner ({'Mål' if is_m else 'Skud'})**")
            st.table(z_counts)
        
        with viz:
            pitch = VerticalPitch(half=True, pitch_type='custom', pitch_length=105, pitch_width=68, line_color='grey')
            fig, ax = pitch.draw(figsize=(8, 10))
            ax.set_ylim(55, 105)
            
            for name, b in ZONE_BOUNDARIES.items():
                if b["y_max"] <= 55: continue
                cnt = len(data[data['ZONE'] == name])
                rect = patches.Rectangle((b["x_min"], max(b["y_min"], 55)), 
                                         b["x_max"]-b["x_min"], b["y_max"]-max(b["y_min"], 55),
                                         facecolor=LIGA_BLUE if cnt > 0 else '#f9f9f9',
                                         alpha=min(cnt/10, 0.8) if cnt > 0 else 0.1, 
                                         edgecolor='black', linestyle='--')
                ax.add_patch(rect)
            st.pyplot(fig)

    with tabs[3]: zone_viz(df_skud, False)
    with tabs[4]: zone_viz(df_skud[df_skud['EVENT_TYPEID'] == 16], True)
