import streamlit as st
import pandas as pd
import numpy as np

# Vi importerer konfigurationen med det rigtige navn
try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "Aktuel Sæson"

def vis_side(spillere_df, stats_df):
    # Dynamisk overskrift baseret på din season_show.py
    st.title(f"🏆 Top 5 Præstationer")
    st.subheader(f"Hvidovre IF | Sæson: {SEASONNAME}")
    
    # 1. Klargør kopier og rens kolonnenavne
    s_info = spillere_df.copy()
    s_stats = stats_df.copy()
    
    s_info.columns = [c.upper().strip() for c in s_info.columns]
    s_stats.columns = [c.upper().strip() for c in s_stats.columns]

    # 2. Find ID-kolonner
    id_s = next((c for c in ['PLAYER_WYID', 'WYID'] if c in s_info.columns), None)
    id_t = next((c for c in ['PLAYER_WYID', 'WYID'] if c in s_stats.columns), None)

    if not id_s or not id_t:
        st.error(f"ID-kolonne mangler!")
        return

    # Robust konvertering af ID'er
    s_info[id_s] = s_info[id_s].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    s_stats[id_t] = s_stats[id_t].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # 3. Forbered Navne og Positioner
    if 'FIRSTNAME' in s_info.columns and 'LASTNAME' in s_info.columns:
        s_info['NAVN_FINAL'] = (s_info['FIRSTNAME'].fillna('') + " " + s_info['LASTNAME'].fillna('')).str.title()
    elif 'NAVN' in s_info.columns:
        s_info['NAVN_FINAL'] = s_info['NAVN'].str.title()
    else:
        s_info['NAVN_FINAL'] = "Ukendt (" + s_info[id_s] + ")"

    pos_map = {'GKP': 'MM', 'DEF': 'FOR', 'MID': 'MID', 'FWD': 'ANG'}
    s_info['POS_DISPLAY'] = s_info['ROLECODE3'].map(pos_map).fillna(s_info.get('ROLECODE3', '-')) if 'ROLECODE3' in s_info.columns else '-'

    # 4. Flet data
    df = pd.merge(s_stats, s_info[[id_s, 'POS_DISPLAY', 'NAVN_FINAL']], left_on=id_t, right_on=id_s, how='inner')

    # --- FIX: FJERN DUBLETTER (Bruger SEASONNAME til at verificere hvis nødvendigt) ---
    m_col_sort = next((c for c in ['MINUTESONFIELD', 'MINUTESTAGGED', 'MINUTES'] if c in df.columns), None)
    if m_col_sort:
        df = df.sort_values(m_col_sort, ascending=False).drop_duplicates(subset=[id_t], keep='first')
    else:
        df = df.drop_duplicates(subset=[id_t], keep='first')

    if df.empty:
        st.warning(f"⚠️ Ingen match fundet for {SEASONNAME}!")
        return

    # 5. KPI Definitioner
    KPI_MAP = {
        'GOALS': 'Mål', 'ASSISTS': 'Assists', 'TOTAL_GOALS': 'Målinvolveringer',
        'SHOTS': 'Skud', 'XGSHOT': 'xG', 'PASSES': 'Pasninger',
        'SUCCESSFULPASSES': 'Vellykkede Pasninger', 'TOUCHINBOX': 'Touch i feltet',
        'PROGRESSIVEPASSES': 'Progressive Pas.', 'DUELS': 'Dueller', 'DUELSWON': 'Dueller Vundet'
    }
    
    CATEGORIES = {
        'Generelt': ['GOALS', 'ASSISTS', 'TOTAL_GOALS', 'SHOTS', 'XGSHOT', 'PASSES'],
        'Offensivt': ['GOALS', 'ASSISTS', 'XGSHOT', 'TOUCHINBOX', 'PROGRESSIVEPASSES'],
        'Dueller': ['DUELS', 'DUELSWON']
    }

    if 'TOTAL_GOALS' not in df.columns:
        df['TOTAL_GOALS'] = pd.to_numeric(df.get('GOALS', 0), errors='coerce').fillna(0) + \
                            pd.to_numeric(df.get('ASSISTS', 0), errors='coerce').fillna(0)

    # 6. UI
    c1, c2 = st.columns(2)
    with c1: valgt_kat = st.selectbox("Vælg Kategori", list(CATEGORIES.keys()))
    with c2: visning = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)
    st.divider()

    kpis = [k for k in CATEGORIES[valgt_kat] if k in df.columns]
    
    for i in range(0, len(kpis), 3):
        cols = st.columns(3)
        for idx, kpi in enumerate(kpis[i:i+3]):
            with cols[idx]:
                temp_df = df.copy()
                temp_df[kpi] = pd.to_numeric(temp_df[kpi], errors='coerce').fillna(0)
                
                m_col = next((c for c in ['MINUTESONFIELD', 'MINUTESTAGGED', 'MINUTES'] if c in temp_df.columns), None)
                mins = pd.to_numeric(temp_df[m_col], errors='coerce').fillna(0) if m_col else pd.Series(0, index=temp_df.index)

                if visning == "Pr. 90":
                    temp_df['VAL'] = np.where(mins > 0, (temp_df[kpi] / mins * 90), 0)
                else:
                    temp_df['VAL'] = temp_df[kpi]

                top5 = temp_df[temp_df['VAL'] > 0].sort_values('VAL', ascending=False).head(5)

                # HTML Tabel
                html = f"""
                <div style="background:#fff; border:1px solid #e6e9ef; border-radius:4px; padding:10px; margin-bottom:15px; min-height:260px;">
                    <h5 style="text-align:center; margin:0 0 10px 0; color:#df003b;">{KPI_MAP.get(kpi, kpi)}</h5>
                    <table style="width:100%; border-collapse:collapse; font-size:13px;">
                        <thead>
                            <tr style="background:#f8f9fb;">
                                <th style="text-align:center; padding:4px; border-bottom:1px solid #ddd; width:15%;">Pos</th>
                                <th style="text-align:left; padding:4px; border-bottom:1px solid #ddd; width:60%;">Spiller</th>
                                <th style="text-align:center; padding:4px; border-bottom:1px solid #ddd; width:25%;">{visning}</th>
                            </tr>
                        </thead>
                        <tbody>"""
                
                for _, r in top5.iterrows():
                    val_str = f"{r['VAL']:.2f}" if (visning == "Pr. 90" or kpi == 'XGSHOT') else f"{int(r['VAL'])}"
                    html += f"""
                            <tr>
                                <td style="text-align:center; padding:4px; border-bottom:1px solid #eee;">{r['POS_DISPLAY']}</td>
                                <td style="text-align:left; padding:4px; border-bottom:1px solid #eee;">{r['NAVN_FINAL']}</td>
                                <td style="text-align:center; padding:4px; border-bottom:1px solid #eee;"><b>{val_str}</b></td>
                            </tr>"""
                
                for _ in range(5 - len(top5)):
                    html += "<tr><td colspan='3' style='padding:4px; border-bottom:1px solid #eee;'>&nbsp;</td></tr>"
                
                html += "</tbody></table></div>"
                st.write(html, unsafe_allow_html=True)
