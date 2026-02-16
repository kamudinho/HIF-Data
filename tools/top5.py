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
        <div style="background-color:#df003b; padding:1px; border-radius:1px; margin-bottom:2px;">
            <h7 style="color:white; margin:0; text-align:center; font-family:sans-serif;">TOP 5 PRÆSTATIONER</h7>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # 2. Kopier og Rens
    s_info = spillere_df.copy()
    s_stats = stats_df.copy()
    
    # Standardiser kolonnenavne til UPPERCASE
    s_info.columns = [str(c).upper().strip() for c in s_info.columns]
    s_stats.columns = [str(c).upper().strip() for c in s_stats.columns]

    # --- ID MATCH FIX ---
    # Vi tvinger PLAYER_WYID til at være en ren tekststreng uden decimaler
    s_info['PLAYER_WYID'] = s_info['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    s_stats['PLAYER_WYID'] = s_stats['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # 3. Merge (Vi bruger NAVN og ROLECODE3 fra din CSV)
    # Vi tager kun de nødvendige kolonner for at undgå rod
    cols_to_use = ['PLAYER_WYID', 'NAVN', 'ROLECODE3']
    df = pd.merge(s_stats, s_info[cols_to_use], on='PLAYER_WYID', how='inner')

    # 4. Dublet-fix (Marvin Egho reglen)
    if 'MINUTESONFIELD' in df.columns:
        df = df.sort_values('MINUTESONFIELD', ascending=False).drop_duplicates(subset=['PLAYER_WYID'])

    if df.empty:
        st.warning(f"⚠️ Ingen match fundet. Tjek om PLAYER_WYID i Snowflake matcher dem i din CSV.")
        return

    # 5. Formatering
    pos_map = {'GKP': 'MM', 'DEF': 'FOR', 'MID': 'MID', 'FWD': 'ANG'}
    df['POS_DISPLAY'] = df['ROLECODE3'].map(pos_map).fillna(df['ROLECODE3'])

    # --- 6. UI KONTROLLER ---
    c1, c2 = st.columns([2, 1])
    with c1:
        valgt_kat = st.pills("Kategori", ["Offensivt", "Generelt"], default="Offensivt")
    with c2:
        visning = st.segmented_control("Visning", ["Total", "Pr. 90"], default="Total")

    KPI_MAP = {
        'GOALS': 'Mål', 'ASSISTS': 'Assists', 'SHOTS': 'Skud', 'XGSHOT': 'xG',
        'TOUCHINBOX': 'Touch i feltet', 'PROGRESSIVEPASSES': 'Prog. Pasninger'
    }
    
    kpis = ['TOUCHINBOX', 'PROGRESSIVEPASSES', 'ASSISTS', 'XGSHOT'] if valgt_kat == "Offensivt" else ['GOALS', 'ASSISTS', 'SHOTS', 'XGSHOT']
    
    # --- 7. RENDER TABELLER ---
    cols = st.columns(2)
    for i, kpi in enumerate(kpis):
        if kpi in df.columns:
            with cols[i % 2]:
                temp_df = df.copy()
                temp_df[kpi] = pd.to_numeric(temp_df[kpi], errors='coerce').fillna(0)
                
                if visning == "Pr. 90" and 'MINUTESONFIELD' in temp_df.columns:
                    temp_df['VAL'] = (temp_df[kpi] / temp_df['MINUTESONFIELD'] * 90).replace([np.inf, -np.inf], 0).fillna(0)
                else:
                    temp_df['VAL'] = temp_df[kpi]

                top5 = temp_df[temp_df['VAL'] > 0].sort_values('VAL', ascending=False).head(5)

                html = f"""
                <div style="background:white; border:1px solid #eee; border-radius:8px; padding:12px; margin-bottom:15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.02);">
                    <h4 style="color:#333; margin:0 0 10px 0; border-bottom: 2px solid #df003b; padding-bottom:3px;">{KPI_MAP.get(kpi, kpi)}</h4>
                    <table style="width:100%; font-size:13px; border-collapse:collapse;">
                        <tr style="color:#888; text-align:center; font-size:10px; text-transform:uppercase;">
                            <th>Pos</th><th>Spiller</th><th style="text-align:center;">{visning}</th>
                        </tr>"""
                for _, r in top5.iterrows():
                    v = f"{r['VAL']:.2f}" if (visning == "Pr. 90" or kpi == 'XGSHOT') else f"{int(r['VAL'])}"
                    html += f"""
                        <tr style="border-bottom:1px solid #f9f9f9;">
                            <td style="padding:8px 0; color:#666;">{r['POS_DISPLAY']}</td>
                            <td style="padding:8px 0; font-weight:500;">{r['NAVN']}</td>
                            <td style="padding:8px 0; text-align:center; font-weight:bold; color:#df003b;">{v}</td>
                        </tr>"""
                html += "</table></div>"
                st.write(html, unsafe_allow_html=True)
