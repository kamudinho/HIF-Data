import streamlit as st
import pandas as pd
import numpy as np

try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "Aktuel Sæson"

def vis_side(spillere_df, stats_df):
    # --- 1. CSS INJECTION (Layout & Centrering) ---
    st.markdown("""
        <style>
            [data-testid="column"] {
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            }
            div[data-testid="stHorizontalBlock"] > div:last-child div[data-testid="stVerticalBlock"] {
                align-items: flex-end !important;
            }
            div[data-testid="stSegmentedControl"] {
                width: fit-content !important;
                margin-left: auto !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. KOMPAKT TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:25px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem;">TOP 5 PRÆSTATIONER</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # 3. Data-klargøring
    s_info = spillere_df.copy()
    s_stats = stats_df.copy()
    s_info.columns = [str(c).upper().strip() for c in s_info.columns]
    s_stats.columns = [str(c).upper().strip() for c in s_stats.columns]

    s_info['PLAYER_WYID'] = s_info['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    s_stats['PLAYER_WYID'] = s_stats['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    df = pd.merge(s_stats, s_info[['PLAYER_WYID', 'NAVN', 'ROLECODE3']], on='PLAYER_WYID', how='inner')
    if 'MINUTESONFIELD' in df.columns:
        df = df.sort_values('MINUTESONFIELD', ascending=False).drop_duplicates(subset=['PLAYER_WYID'])

    if df.empty:
        st.warning(f"⚠️ Ingen match fundet.")
        return

    pos_map = {'GKP': 'MM', 'DEF': 'FOR', 'MID': 'MID', 'FWD': 'ANG'}
    df['POS_DISPLAY'] = df['ROLECODE3'].map(pos_map).fillna(df['ROLECODE3'])

    # --- 4. KNAPPER ---
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        valgt_kat = st.pills("Kategori", ["Offensivt", "Generelt"], default="Offensivt", label_visibility="collapsed")
    with c2:
        visning = st.segmented_control("Visning", ["Total", "Pr. 90"], default="Total", label_visibility="collapsed")

    KPI_MAP = {
        'GOALS': 'Mål', 'ASSISTS': 'Assists', 'SHOTS': 'Skud', 'XGSHOT': 'xG',
        'TOUCHINBOX': 'Touch i feltet', 'PROGRESSIVEPASSES': 'Prog. Pasninger'
    }
    
    if valgt_kat == "Offensivt":
        kpis = ['TOUCHINBOX', 'PROGRESSIVEPASSES', 'ASSISTS', 'XGSHOT', 'GOALS', 'SHOTS']
    else:
        kpis = ['GOALS', 'ASSISTS', 'SHOTS', 'XGSHOT', 'TOUCHINBOX', 'PROGRESSIVEPASSES']

    st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)

    # --- 5. RENDER KOMPAKTE TABELLER ---
    cols = st.columns(3)
    for i, kpi in enumerate(kpis):
        if kpi in df.columns:
            with cols[i % 3]:
                temp_df = df.copy()
                temp_df[kpi] = pd.to_numeric(temp_df[kpi], errors='coerce').fillna(0)
                
                if visning == "Pr. 90" and 'MINUTESONFIELD' in temp_df.columns:
                    temp_df['VAL'] = (temp_df[kpi] / temp_df['MINUTESONFIELD'] * 90).replace([np.inf, -np.inf], 0).fillna(0)
                else:
                    temp_df['VAL'] = temp_df[kpi]

                top5 = temp_df[temp_df['VAL'] > 0].sort_values('VAL', ascending=False).head(5)

                html = f"""
                <div style="background:white; border:1px solid #eee; border-radius:4px; padding:0px; margin-bottom:15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                    <div style="padding:6px 10px; border-bottom: 2px solid #df003b; background:#fff;">
                        <h4 style="color:#333; margin:0; font-family:sans-serif; font-size:14px; text-transform:uppercase; font-weight:700;">{KPI_MAP.get(kpi, kpi)}</h4>
                    </div>
                    <table style="width:100%; font-size:14px; border-collapse:collapse; font-family:sans-serif;">
                        <tr style="color:#888; font-size:10px; text-transform:uppercase; background:#fafafa; border-bottom: 1px solid #eee;">
                            <th style="padding:4px 5px; width:45px; text-align:center;">Pos</th>
                            <th style="padding:4px 10px; text-align:left;">Spiller</th>
                            <th style="padding:4px 5px; width:60px; text-align:center;">{visning}</th>
                        </tr>"""
                
                for _, r in top5.iterrows():
                    v = f"{r['VAL']:.2f}" if (visning == "Pr. 90" or kpi == 'XGSHOT') else f"{int(r['VAL'])}"
                    html += f"""
                        <tr style="border-bottom:1px solid #f9f9f9;">
                            <td style="padding:4px 5px; color:#666; font-size:12px; text-align:center;">{r['POS_DISPLAY']}</td>
                            <td style="padding:4px 10px; font-weight:500; color:#222; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100px;">{r['NAVN']}</td>
                            <td style="padding:4px 5px; text-align:center; font-weight:700; color:#df003b;">{v}</td>
                        </tr>"""
                
                html += "</table></div>"
                st.write(html, unsafe_allow_html=True)
