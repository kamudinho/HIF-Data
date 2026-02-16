import streamlit as st
import pandas as pd
import numpy as np

# Vi importerer konfigurationen
try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "Aktuel Sæson"

def vis_side(spillere_df, stats_df):
    st.title(f"🏆 Top 5 Præstationer")
    st.subheader(f"Hvidovre IF | Sæson: {SEASONNAME}")
    
    # 1. Klargør data
    # Vi tager stats fra Snowflake og kobler dem på spillere fra din csv
    s_info = spillere_df.copy()
    s_stats = stats_df.copy()
    
    # Tving alle kolonnenavne til UPPERCASE for at undgå fejl
    s_info.columns = [c.upper().strip() for c in s_info.columns]
    s_stats.columns = [c.upper().strip() for c in s_stats.columns]

    # 2. Kobling (Merge) på PLAYER_WYID
    # Vi sikrer os at begge kolonner er strenge (strings) uden .0
    for d in [s_info, s_stats]:
        if 'PLAYER_WYID' in d.columns:
            d['PLAYER_WYID'] = d['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # Nu fletter vi - vi tager kun de spillere der findes i din players.csv
    df = pd.merge(s_stats, s_info, on='PLAYER_WYID', how='inner')

    # --- 3. DUBLET-FIX (Marvin Egho reglen) ---
    # Vi sorterer efter minutter og beholder kun den største række pr. spiller
    if 'MINUTESONFIELD' in df.columns:
        df = df.sort_values('MINUTESONFIELD', ascending=False).drop_duplicates(subset=['PLAYER_WYID'])

    # 4. Navne-formatering (bruger kolonnerne fra din csv)
    if 'FIRSTNAME' in df.columns and 'LASTNAME' in df.columns:
        df['NAVN_DISPLAY'] = (df['FIRSTNAME'].fillna('') + " " + df['LASTNAME'].fillna('')).str.title()
    else:
        df['NAVN_DISPLAY'] = df['PLAYER_WYID']

    # Positioner (HIF-format)
    pos_map = {'GKP': 'MM', 'DEF': 'FOR', 'MID': 'MID', 'FWD': 'ANG'}
    df['POS_DISPLAY'] = df['ROLECODE3'].map(pos_map).fillna(df.get('ROLECODE3', '-'))

    if df.empty:
        st.warning("Ingen data fundet efter kobling med players.csv")
        return

    # --- 5. VISNING ---
    KPI_MAP = {
        'GOALS': 'Mål', 'ASSISTS': 'Assists', 'SHOTS': 'Skud', 'XGSHOT': 'xG',
        'PASSES': 'Pasninger', 'SUCCESSFULPASSES': 'Vellykkede Pas.',
        'TOUCHINBOX': 'Touch i feltet', 'PROGRESSIVEPASSES': 'Progressive Pas.'
    }
    
    cat_options = ["Generelt", "Offensivt"]
    valgt_kat = st.selectbox("Vælg Kategori", cat_options)
    visning = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)
    st.divider()

    kpis = ['GOALS', 'ASSISTS', 'SHOTS', 'XGSHOT'] if valgt_kat == "Generelt" else ['TOUCHINBOX', 'PROGRESSIVEPASSES', 'ASSISTS', 'XGSHOT']
    
    for i in range(0, len(kpis), 2): # Viser 2 kolonner for bedre plads
        cols = st.columns(2)
        for idx, kpi in enumerate(kpis[i:i+2]):
            if kpi in df.columns:
                with cols[idx]:
                    temp_df = df.copy()
                    val_col = 'VAL'
                    
                    if visning == "Pr. 90" and 'MINUTESONFIELD' in temp_df.columns:
                        temp_df[val_col] = (temp_df[kpi] / temp_df['MINUTESONFIELD'] * 90).replace([np.inf, -np.inf], 0).fillna(0)
                    else:
                        temp_df[val_col] = temp_df[kpi]

                    top5 = temp_df[temp_df[val_col] > 0].sort_values(val_col, ascending=False).head(5)

                    # Din HTML Skabelon
                    html = f"""
                    <div style="background:#fff; border:1px solid #e6e9ef; border-radius:4px; padding:10px; margin-bottom:15px;">
                        <h5 style="text-align:center; margin:0 0 10px 0; color:#df003b;">{KPI_MAP.get(kpi, kpi)}</h5>
                        <table style="width:100%; border-collapse:collapse; font-size:13px;">
                            <tr style="background:#f8f9fb;">
                                <th style="text-align:center; width:15%;">Pos</th>
                                <th style="text-align:left; width:60%;">Spiller</th>
                                <th style="text-align:center; width:25%;">{visning}</th>
                            </tr>"""
                    for _, r in top5.iterrows():
                        v = f"{r[val_col]:.2f}" if (visning == "Pr. 90" or kpi == 'XGSHOT') else f"{int(r[val_col])}"
                        html += f"""
                            <tr>
                                <td style="text-align:center; border-bottom:1px solid #eee;">{r['POS_DISPLAY']}</td>
                                <td style="text-align:left; border-bottom:1px solid #eee;">{r['NAVN_DISPLAY']}</td>
                                <td style="text-align:center; border-bottom:1px solid #eee;"><b>{v}</b></td>
                            </tr>"""
                    html += "</table></div>"
                    st.write(html, unsafe_allow_html=True)
