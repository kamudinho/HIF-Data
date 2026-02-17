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

    # --- 3. DATA-KLARGØRING ---
    s_info = spillere_df.copy()
    s_stats = stats_df.copy()
    
    # Standardiser kolonnenavne til UPPERCASE
    s_info.columns = [str(c).upper().strip() for c in s_info.columns]
    s_stats.columns = [str(c).upper().strip() for c in s_stats.columns]

    # Rens ID'er
    s_info['PLAYER_WYID'] = s_info['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    s_stats['PLAYER_WYID'] = s_stats['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # Merge stats med spillerinfo
    df = pd.merge(s_stats, s_info[['PLAYER_WYID', 'NAVN', 'ROLECODE3']], on='PLAYER_WYID', how='inner')
    
    # Vi bruger MINUTESONFIELD fra din Snowflake-liste
    if 'MINUTESONFIELD' in df.columns:
        df = df.sort_values('MINUTESONFIELD', ascending=False).drop_duplicates(subset=['PLAYER_WYID'])

    if df.empty:
        st.warning(f"⚠️ Ingen match fundet mellem spillere og statistikker.")
        return

    pos_map = {'GKP': 'MM', 'DEF': 'FOR', 'MID': 'MID', 'FWD': 'ANG'}
    df['POS_DISPLAY'] = df['ROLECODE3'].map(pos_map).fillna(df['ROLECODE3'])

    # --- 4. NAVIGATION / FILTRE ---
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        valgt_kat = st.pills("Type", ["Offensivt", "Distribution", "Defensivt"], default="Offensivt", label_visibility="collapsed")
    with c2:
        visning = st.segmented_control("Enhed", ["Total", "Pr. 90"], default="Total", label_visibility="collapsed")

    # --- 5. KPI DEFINITIONER (Baseret på din Snowflake liste) ---
    KPI_MAP = {
        'GOALS': 'Mål', 
        'ASSISTS': 'Assists', 
        'XGSHOT': 'xG',
        'SHOTS': 'Skud',
        'TOUCHINBOX': 'Touch i feltet', 
        'PROGRESSIVEPASSES': 'Prog. Pasninger',
        'PROGRESSIVERUN': 'Prog. Løb',
        'SMARTPASSES': 'Smart Pasninger',
        'DRIBBLES': 'Driblinger',
        'DUELSWON': 'Dueller Vundet',
        'INTERCEPTIONS': 'Opspininger',
        'RECOVERIES': 'Erobringer'
    }
    
    if valgt_kat == "Offensivt":
        kpis = ['GOALS', 'XGSHOT', 'ASSISTS', 'SHOTS', 'TOUCHINBOX', 'DRIBBLES']
    elif valgt_kat == "Distribution":
        kpis = ['PROGRESSIVEPASSES', 'PROGRESSIVERUN', 'SMARTPASSES', 'ASSISTS', 'TOUCHINBOX', 'SHOTASSISTS']
    else: # Defensivt
        kpis = ['DUELSWON', 'INTERCEPTIONS', 'RECOVERIES', 'CLEARANCES', 'FOULS', 'YELLOWCARDS']

    st.markdown("<div style='margin-bottom:15px;'></div>", unsafe_allow_html=True)

    # --- 6. RENDER KOMPAKTE TABELLER ---
    cols = st.columns(3)
    # Filtrer KPI'er der faktisk findes i den indsendte dataframe
    aktive_kpis = [k for k in kpis if k in df.columns]

    for i, kpi in enumerate(aktive_kpis):
        with cols[i % 3]:
            temp_df = df.copy()
            temp_df[kpi] = pd.to_numeric(temp_df[kpi], errors='coerce').fillna(0)
            
            # Beregning
            if visning == "Pr. 90" and 'MINUTESONFIELD' in temp_df.columns:
                # Undgå division med nul
                temp_df['VAL'] = (temp_df[kpi] / temp_df['MINUTESONFIELD'].replace(0, np.nan) * 90).fillna(0)
            else:
                temp_df['VAL'] = temp_df[kpi]

            # Tag kun spillere med en værdi over 0 og sorter
            top5 = temp_df[temp_df['VAL'] > 0].sort_values('VAL', ascending=False).head(5)

            # HTML Tabel Render
            html = f"""
            <div style="background:white; border:1px solid #eee; border-radius:4px; padding:0px; margin-bottom:15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
                <div style="padding:6px 10px; border-bottom: 2px solid #df003b; background:#fff;">
                    <h4 style="color:#333; margin:0; font-family:sans-serif; font-size:13px; text-transform:uppercase; font-weight:700;">{KPI_MAP.get(kpi, kpi)}</h4>
                </div>
                <table style="width:100%; font-size:13px; border-collapse:collapse; font-family:sans-serif;">
                    <tr style="color:#888; font-size:9px; text-transform:uppercase; background:#fafafa; border-bottom: 1px solid #eee;">
                        <th style="padding:4px 5px; width:40px; text-align:center;">Pos</th>
                        <th style="padding:4px 10px; text-align:left;">Spiller</th>
                        <th style="padding:4px 5px; width:55px; text-align:center;">{visning}</th>
                    </tr>"""
            
            if top5.empty:
                html += f'<tr><td colspan="3" style="padding:10px; text-align:center; color:#ccc; font-style:italic;">Ingen data</td></tr>'
            else:
                for _, r in top5.iterrows():
                    # Formatering: xG og Pr. 90 skal have decimaler, ellers heltal
                    is_decimal = (visning == "Pr. 90" or kpi in ['XGSHOT', 'XGASSIST'])
                    v = f"{r['VAL']:.2f}" if is_decimal else f"{int(r['VAL'])}"
                    
                    html += f"""
                        <tr style="border-bottom:1px solid #f9f9f9;">
                            <td style="padding:4px 5px; color:#666; font-size:11px; text-align:center;">{r['POS_DISPLAY']}</td>
                            <td style="padding:4px 10px; font-weight:500; color:#222; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 90px;">{r['NAVN']}</td>
                            <td style="padding:4px 5px; text-align:center; font-weight:700; color:#df003b;">{v}</td>
                        </tr>"""
            
            html += "</table></div>"
            st.write(html, unsafe_allow_html=True)
