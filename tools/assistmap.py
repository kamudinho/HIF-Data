import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from mplsoccer import VerticalPitch

# HIF Identitet
HIF_RED = '#cc0000'
HIF_GOLD = '#b8860b'

# --- 1. DINE PRÆCISE ZONE-DEFINITIONER (FRA PITCH_ANALYSIS.PY) ---
PITCH_LENGTH = 105
PITCH_WIDTH = 68
CENTER_ZONE_WIDTH = 18.32
X_CENTER_MIN = (PITCH_WIDTH - CENTER_ZONE_WIDTH) / 2
X_CENTER_MAX = (PITCH_WIDTH + CENTER_ZONE_WIDTH) / 2

Y_GOALLINE = 105.0
Y_SIX_YARD = 99.5
Y_PENALTY_SPOT = 94.0
Y_PENALTY_AREA = 88.5
Y_MID_DEFENSE = 75.0
X_WIDE_INNER_MAX = (PITCH_WIDTH + 40.2) / 2
X_WIDE_INNER_MIN = (PITCH_WIDTH - 40.2) / 2

ZONE_BOUNDARIES = {
    "Zone 1": {"y_min": Y_SIX_YARD, "y_max": Y_GOALLINE, "x_min": X_CENTER_MIN, "x_max": X_CENTER_MAX},
    "Zone 2": {"y_min": Y_PENALTY_SPOT, "y_max": Y_SIX_YARD, "x_min": X_CENTER_MIN, "x_max": X_CENTER_MAX},
    "Zone 3": {"y_min": Y_PENALTY_AREA, "y_max": Y_PENALTY_SPOT, "x_min": X_CENTER_MIN, "x_max": X_CENTER_MAX},
    "Zone 4A": {"y_min": Y_SIX_YARD, "y_max": Y_GOALLINE, "x_min": X_CENTER_MAX, "x_max": X_WIDE_INNER_MAX},
    "Zone 4B": {"y_min": Y_SIX_YARD, "y_max": Y_GOALLINE, "x_min": X_WIDE_INNER_MIN, "x_max": X_CENTER_MIN},
    "Zone 5A": {"y_min": Y_PENALTY_AREA, "y_max": Y_SIX_YARD, "x_min": X_CENTER_MAX, "x_max": X_WIDE_INNER_MAX},
    "Zone 5B": {"y_min": Y_PENALTY_AREA, "y_max": Y_SIX_YARD, "x_min": X_WIDE_INNER_MIN, "x_max": X_CENTER_MIN},
    "Zone 6A": {"y_min": Y_PENALTY_AREA, "y_max": Y_GOALLINE, "x_min": X_WIDE_INNER_MAX, "x_max": PITCH_WIDTH},
    "Zone 6B": {"y_min": Y_PENALTY_AREA, "y_max": Y_GOALLINE, "x_min": 0, "x_max": X_WIDE_INNER_MIN},
    "Zone 7B": {"y_min": Y_MID_DEFENSE, "y_max": Y_PENALTY_AREA, "x_min": X_CENTER_MIN, "x_max": X_CENTER_MAX},
    "Zone 7C": {"y_min": Y_MID_DEFENSE, "y_max": Y_PENALTY_AREA, "x_min": 0, "x_max": X_CENTER_MIN},
    "Zone 7A": {"y_min": Y_MID_DEFENSE, "y_max": Y_PENALTY_AREA, "x_min": X_CENTER_MAX, "x_max": PITCH_WIDTH},
    "Zone 8": {"y_min": 0, "y_max": Y_MID_DEFENSE, "x_min": 0, "x_max": PITCH_WIDTH}
}

def get_zone_from_coords(x_meter, y_meter):
    """Matcher en koordinat med dine ZONE_BOUNDARIES definitioner"""
    for zone, b in ZONE_BOUNDARIES.items():
        if (b["y_min"] <= y_meter <= b["y_max"]) and (b["x_min"] <= x_meter <= b["x_max"]):
            return zone
    return "Udenfor"

def vis_side(dp):
    # CSS Styling
    st.markdown(f"""
        <style>
            .full-width-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            .full-width-table th {{ background-color: #f0f2f6; text-align: left; padding: 10px; border-bottom: 2px solid {HIF_GOLD}; font-size: 0.85rem; }}
            .full-width-table td {{ padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 0.9rem; }}
            .stat-box {{ background-color: #f8f9fa; padding: 8px 12px; border-radius: 8px; border-left: 5px solid {HIF_GOLD}; margin-bottom: 8px; }}
            .stat-label {{ font-size: 0.75rem; text-transform: uppercase; color: #666; font-weight: bold; display: flex; align-items: center; gap: 8px; }}
            .stat-value {{ font-size: 1.4rem; font-weight: 800; color: #1a1a1a; margin-top: 2px; }}
            .icon-circle {{ width: 12px; height: 12px; border-radius: 50%; display: inline-block; border: 1.5px solid black; }}
        </style>
    """, unsafe_allow_html=True)
    
    df_assists = dp.get('assists', pd.DataFrame()).copy()
    if df_assists.empty:
        st.caption("Ingen data fundet.")
        return

    # Forberedelse (Konverter Opta 0-100 til dine meter-mål)
    df_assists['x_meter'] = df_assists['PASS_START_Y'] * (PITCH_WIDTH / 100) # Opta Y er bredde
    df_assists['y_meter'] = df_assists['PASS_START_X'] * (PITCH_LENGTH / 100) # Opta X er længde
    df_assists['is_assist'] = (df_assists['NEXT_EVENT_TYPE'] == 16).astype(int)
    df_assists['is_key_pass'] = df_assists['NEXT_EVENT_TYPE'].isin([13, 14, 15]).astype(int)
    
    # Tildel zoner baseret på dine grænser
    df_assists['Zone'] = df_assists.apply(lambda r: get_zone_from_coords(r['x_meter'], r['y_meter']), axis=1)

    tab1, tab2, tab3 = st.tabs(["ASSIST-OVERSIGT", "ASSIST-MAP", "ASSIST-ZONER"])

    # --- TAB 1: OVERSIGT ---
    with tab1:
        df_table = df_assists.groupby('ASSIST_PLAYER').agg(
            Assists=('is_assist', 'sum'),
            Key_Passes=('is_key_pass', 'sum'),
            Corner_Assists=('IS_CORNER', 'sum'),
            Cross_Assists=('IS_CROSS', 'sum'),
            Progressive=('IS_PROGRESSIVE', 'sum')
        ).reset_index().sort_values(["Assists", "Key_Passes"], ascending=False)

        table_html = '<table class="full-width-table"><thead><tr>'
        for col in ["Spiller", "Assists", "Key Passes", "Corner", "Cross", "Prog."]:
            table_html += f'<th>{col}</th>'
        table_html += '</tr></thead><tbody>'
        for _, row in df_table.iterrows():
            table_html += f"<tr><td><b>{row['ASSIST_PLAYER']}</b></td><td>{row['Assists']}</td><td>{row['Key_Passes']}</td><td>{row['Corner_Assists']}</td><td>{row['Cross_Assists']}</td><td>{row['Progressive']}</td></tr>"
        table_html += '</tbody></table>'
        st.markdown(table_html, unsafe_allow_html=True)

    # --- TAB 2: MAP ---
    with tab2:
        col_viz, col_ctrl = st.columns([1.8, 1])
        with col_ctrl:
            v_a = st.selectbox("Vælg spiller", options=["Hvidovre IF"] + sorted(df_table["ASSIST_PLAYER"].tolist()))
            df_f = df_assists[df_assists['ASSIST_PLAYER'] == v_a] if v_a != "Hvidovre IF" else df_assists
            st.markdown(f'<div class="stat-box"><div class="stat-label"><span class="icon-circle" style="background-color: {HIF_GOLD};"></span>Goal Assists</div><div class="stat-value">{df_f["is_assist"].sum()}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="stat-box" style="border-left-color: #888888"><div class="stat-label"><span class="icon-circle" style="background-color: #888888;"></span>Shot Assists</div><div class="stat-value">{df_f["is_key_pass"].sum()}</div></div>', unsafe_allow_html=True)

        with col_viz:
            pitch = VerticalPitch(half=True, pitch_type='opta', pitch_color='white', line_color='#cccccc')
            fig, ax = pitch.draw(figsize=(8, 6))
            # Tegn assists (kunne udvides med pile)
            df_gs = df_f[df_f['is_assist'] == 1]
            pitch.scatter(df_gs['PASS_START_X'], df_gs['PASS_START_Y'], s=100, color=HIF_GOLD, edgecolors='black', ax=ax, zorder=3)
            st.pyplot(fig, use_container_width=True)

    # --- TAB 3: ASSIST-ZONER (DIN MODEL) ---
    with tab3:
        col_z_map, col_z_data = st.columns([1.8, 1])
        df_z = df_assists[df_assists['is_assist'] == 1].copy()
        
        with col_z_data:
            st.markdown("**ASSISTS PR. ZONE**")
            z_summary = df_z['Zone'].value_counts().reindex(ZONE_BOUNDARIES.keys(), fill_value=0).reset_index()
            z_summary.columns = ['Zone', 'Antal']
            st.table(z_summary[z_summary['Antal'] > 0]) # Vis kun zoner med data

        with col_z_map:
            # Vi bruger din logik fra create_pitch_map
            pitch_z = VerticalPitch(half=True, pitch_type='custom', pitch_length=PITCH_LENGTH, pitch_width=PITCH_WIDTH,
                                    line_color='grey', goal_type='box')
            fig_z, ax_z = pitch_z.draw(figsize=(8, 10))
            ax_z.set_ylim(50, 105)

            # Tegn dine rektangler præcis som i dit script
            for name, bounds in ZONE_BOUNDARIES.items():
                if bounds["y_max"] <= 50: continue
                rect = Rectangle((bounds["x_min"], max(bounds["y_min"], 50)), 
                                 bounds["x_max"] - bounds["x_min"], 
                                 bounds["y_max"] - max(bounds["y_min"], 50),
                                 edgecolor='black', linestyle='--', facecolor=HIF_GOLD, alpha=0.1)
                ax_z.add_patch(rect)
                # Tilføj zonenavn
                ax_z.text(bounds["x_min"] + (bounds["x_max"] - bounds["x_min"])/2,
                          bounds["y_min"] + (bounds["y_max"] - bounds["y_min"])/2,
                          name, ha='center', va='center', fontsize=8, alpha=0.5)

            # Plot de faktiske assists på zone-kortet
            if not df_z.empty:
                pitch_z.scatter(df_z['y_meter'], df_z['x_meter'], s=100, color=HIF_GOLD, edgecolors='black', ax=ax_z, zorder=5)
            
            st.pyplot(fig_z, use_container_width=True)
