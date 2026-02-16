import streamlit as st
import pandas as pd
import numpy as np

# Vi importerer konfigurationen dynamisk
try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "Aktuel Sæson"

def vis_side(spillere_df, stats_df):
    # --- 1. RENT DESIGN (Fjerner standard overskrifter) ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:10px; border-radius:5px; margin-bottom:20px;">
            <h3 style="color:white; margin:0; text-align:center;">TOP 5 PRÆSTATIONER</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # 2. Klargør data
    s_info = spillere_df.copy()
    s_stats = stats_df.copy()
    
    # Tving alle kolonnenavne til UPPERCASE
    s_info.columns = [c.upper().strip() for c in s_info.columns]
    s_stats.columns = [c.upper().strip() for c in s_stats.columns]

    # --- KRITISK FIX: Sikrer ens format på PLAYER_WYID ---
    def clean_id(column):
        return column.astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    if 'PLAYER_WYID' in s_info.columns:
        s_info['PLAYER_WYID'] = clean_id(s_info['PLAYER_WYID'])
    if 'PLAYER_WYID' in s_stats.columns:
        s_stats['PLAYER_WYID'] = clean_id(s_stats['PLAYER_WYID'])

    # 3. Kobling (Merge) - Vi bruger INNER for kun at få spillere fra din players.csv
    df = pd.merge(s_stats, s_info[['PLAYER_WYID', 'FIRSTNAME', 'LASTNAME', 'ROLECODE3']], on='PLAYER_WYID', how='inner')

    # --- 4. DUBLET-FIX ---
    if 'MINUTESONFIELD' in df.columns:
        df = df.sort_values('MINUTESONFIELD', ascending=False).drop_duplicates(subset=['PLAYER_WYID'])

    # 5. Navne-formatering
    df['NAVN_DISPLAY'] = (df['FIRSTNAME'].fillna('') + " " + df['LASTNAME'].fillna('')).str.title()
    
    pos_map = {'GKP': 'MM', 'DEF': 'FOR', 'MID': 'MID', 'FWD': 'ANG'}
    df['POS_DISPLAY'] = df['ROLECODE3'].map(pos_map).fillna(df.get('ROLECODE3', '-'))

    if df.empty:
        st.warning(f"⚠️ Ingen match fundet mellem Snowflake og players.csv for {SEASONNAME}")
        return

    # --- 6. VISNING ---
    KPI_MAP = {
        'GOALS': 'Mål', 'ASSISTS': 'Assists', 'SHOTS': 'Skud', 'XGSHOT': 'xG',
        'PASSES': 'Pasninger', 'SUCCESSFULPASSES': 'Vellykkede Pas.',
        'TOUCHINBOX': 'Touch i feltet', 'PROGRESSIVEPASSES': 'Prog. Pasninger'
    }
    
    c1, c2 = st.columns([2, 1])
    with c1:
        valgt_kat = st.pills("Vælg Kategori", ["Generelt", "Offensivt"], default="Offensivt")
    with c2:
        visning = st.segmented_control("Visning", ["Total", "Pr. 90"], default="Total")

    st.markdown("<br>", unsafe_allow_html=True)

    kpis = ['GOALS', 'ASSISTS', 'SHOTS', 'XGSHOT'] if valgt_kat == "Generelt" else ['TOUCHINBOX', 'PROGRESSIVEPASSES', 'ASSISTS', 'XGSHOT']
    
    cols = st.columns(2)
    for i, kpi in enumerate(kpis):
        if kpi in df.columns:
            with cols[i % 2]:
                temp_df = df.copy()
                # Sikrer numerisk data
                temp_df[kpi] = pd.to_numeric(temp_df[kpi], errors='coerce').fillna(0)
                
                if visning == "Pr. 90" and 'MINUTESONFIELD' in temp_df.columns:
                    temp_df['VAL'] = (temp_df[kpi] / temp_df['MINUTESONFIELD'] * 90).replace([np.inf, -np.inf], 0).fillna(0)
                else:
                    temp_df['VAL'] = temp_df[kpi]

                top5 = temp_df[temp_df['VAL'] > 0].sort_values('VAL', ascending=False).head(5)

                html = f"""
                <div style="background:#fff; border:1px solid #eee; border-radius:8px; padding:12px; margin-bottom:15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
                    <h4 style="color:#333; margin:0 0 10px 0; border-bottom: 2px solid #df003b;">{KPI_MAP.get(kpi, kpi)}</h4>
                    <table style="width:100%; font-size:13px; border-collapse:collapse;">
                        <tr style="color:#888; text-align:left; font-size:11px;">
                            <th>POS</th><th>SPILLER</th><th style="text-align:right;">{visning}</th>
                        </tr>"""
                for _, r in top5.iterrows():
                    v = f"{r['VAL']:.2f}" if (visning == "Pr. 90" or kpi == 'XGSHOT') else f"{int(r['VAL'])}"
                    html += f"""
                        <tr style="border-bottom:1px solid #f9f9f9;">
                            <td style="padding:5px 0;">{r['POS_DISPLAY']}</td>
                            <td style="padding:5px 0; font-weight:500;">{r['NAVN_DISPLAY']}</td>
                            <td style="padding:5px 0; text-align:right; font-weight:bold; color:#df003b;">{v}</td>
                        </tr>"""
                html += "</table></div>"
                st.write(html, unsafe_allow_html=True)
