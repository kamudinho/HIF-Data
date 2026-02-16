import streamlit as st
import pandas as pd
import numpy as np

try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "Aktuel Sæson"

def vis_side(spillere_df, stats_df):
    # --- 1. RENT DESIGN (HIF BRANDING) ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:15px; border-radius:8px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.2rem;">TOP 5 PRÆSTATIONER</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.9;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # 2. Kopier og Rens
    s_info = spillere_df.copy()
    s_stats = stats_df.copy()
    
    s_info.columns = [str(c).upper().strip() for c in s_info.columns]
    s_stats.columns = [str(c).upper().strip() for c in s_stats.columns]

    # ID MATCH FIX
    s_info['PLAYER_WYID'] = s_info['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    s_stats['PLAYER_WYID'] = s_stats['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # 3. Merge
    cols_to_use = ['PLAYER_WYID', 'NAVN', 'ROLECODE3']
    df = pd.merge(s_stats, s_info[cols_to_use], on='PLAYER_WYID', how='inner')

    # 4. Dublet-fix
    if 'MINUTESONFIELD' in df.columns:
        df = df.sort_values('MINUTESONFIELD', ascending=False).drop_duplicates(subset=['PLAYER_WYID'])

    if df.empty:
        st.warning(f"⚠️ Ingen match fundet for {SEASONNAME}")
        return

    # 5. Formatering af positioner
    pos_map = {'GKP': 'MM', 'DEF': 'FOR', 'MID': 'MID', 'FWD': 'ANG'}
    df['POS_DISPLAY'] = df['ROLECODE3'].map(pos_map).fillna(df['ROLECODE3'])

    # --- 6. KPI DEFINITION (Faste kategorier nu hvor vælgeren er væk) ---
    # Jeg har valgt de 6 vigtigste stats til et samlet overblik
    KPI_DISPLAY = [
        ('GOALS', 'Mål'), 
        ('ASSISTS', 'Assists'), 
        ('XGSHOT', 'xG (Total)'),
        ('TOUCHINBOX', 'Touch i feltet'),
        ('SHOTS', 'Skud'),
        ('PROGRESSIVEPASSES', 'Prog. Pasninger')
    ]
    
    # --- 7. RENDER TABELLER (2-kolonne grid) ---
    cols = st.columns(2)
    for i, (kpi, label) in enumerate(KPI_DISPLAY):
        if kpi in df.columns:
            with cols[i % 2]:
                temp_df = df.copy()
                temp_df[kpi] = pd.to_numeric(temp_df[kpi], errors='coerce').fillna(0)
                temp_df['VAL'] = temp_df[kpi]

                # Find top 5 (kun spillere med værdi > 0)
                top5 = temp_df[temp_df['VAL'] > 0].sort_values('VAL', ascending=False).head(5)

                html = f"""
                <div style="background:white; border:1px solid #eee; border-radius:8px; padding:12px; margin-bottom:15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.02);">
                    <h4 style="color:#333; margin:0 0 10px 0; border-bottom: 2px solid #df003b; padding-bottom:5px; font-family:sans-serif; font-size:14px;">{label}</h4>
                    <table style="width:100%; font-size:12px; border-collapse:collapse; font-family:sans-serif;">
                        <tr style="color:#888; text-align:left; font-size:10px; text-transform:uppercase; border-bottom: 1px solid #f0f0f0;">
                            <th style="padding:4px 0;">Pos</th>
                            <th style="padding:4px 0;">Spiller</th>
                            <th style="padding:4px 0; text-align:right;">Antal</th>
                        </tr>"""
                
                for _, r in top5.iterrows():
                    # Formatering: xG får decimaler, resten er heltal
                    v = f"{r['VAL']:.2f}" if kpi == 'XGSHOT' else f"{int(r['VAL'])}"
                    html += f"""
                        <tr>
                            <td style="padding:8px 0; color:#666; width:40px;">{r['POS_DISPLAY']}</td>
                            <td style="padding:8px 0; font-weight:500; color:#222;">{r['NAVN']}</td>
                            <td style="padding:8px 0; text-align:right; font-weight:bold; color:#df003b;">{v}</td>
                        </tr>"""
                
                html += "</table></div>"
                st.write(html, unsafe_allow_html=True)
