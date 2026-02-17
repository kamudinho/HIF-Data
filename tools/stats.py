import streamlit as st
import pandas as pd
import numpy as np

try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "Aktuel Sæson"

def vis_side(spillere, player_stats_sn):
    # --- 1. CSS INJECTION (Matcher Top 5 Layout) ---
    st.markdown("""
        <style>
            .block-container {
                padding-top: 1rem !important;
                max-width: 98% !important;
            }
            [data-testid="column"] {
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            }
            /* Tvinger visnings-knapperne helt til højre */
            div[data-testid="stHorizontalBlock"] > div:last-child div[data-testid="stVerticalBlock"] {
                align-items: flex-end !important;
            }
            div[data-testid="stSegmentedControl"] {
                width: fit-content !important;
                margin-left: auto !important;
            }
            /* Styling af de custom barer */
            .stat-row {
                display: flex;
                align-items: center;
                margin-bottom: 8px;
                font-family: sans-serif;
            }
            .stat-name {
                width: 150px;
                font-size: 13px;
                font-weight: 500;
                color: #222;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .stat-bar-container {
                flex-grow: 1;
                background: #f0f0f0;
                height: 18px;
                border-radius: 2px;
                margin: 0 10px;
                position: relative;
            }
            .stat-bar-fill {
                background: #df003b;
                height: 100%;
                border-radius: 2px;
            }
            .stat-value {
                width: 70px;
                font-size: 13px;
                font-weight: 700;
                color: #df003b;
                text-align: right;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. BRANDING ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:25px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem;">SPILLER STATISTIK</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 3. DATA-KLARGØRING ---
    s_info = spillere.copy()
    s_stats = player_stats_sn.copy()
    s_info.columns = [str(c).upper().strip() for c in s_info.columns]
    s_stats.columns = [str(c).upper().strip() for c in s_stats.columns]

    s_info['PLAYER_WYID'] = s_info['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    s_stats['PLAYER_WYID'] = s_stats['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    if 'SEASONNAME' in s_stats.columns:
        df_stats = s_stats[s_stats['SEASONNAME'] == SEASONNAME].copy()
    else:
        df_stats = s_stats.copy()

    spillere_clean = s_info.drop_duplicates(subset=['PLAYER_WYID'])
    if 'NAVN' not in spillere_clean.columns:
        spillere_clean['NAVN'] = (spillere_clean['FIRSTNAME'].fillna('') + " " + spillere_clean['LASTNAME'].fillna('')).str.strip()

    df_hif = pd.merge(df_stats, spillere_clean[['PLAYER_WYID', 'NAVN']], on='PLAYER_WYID', how='inner')

    if df_hif.empty:
        st.warning("Ingen data fundet.")
        return

    # --- 4. KNAPPER (Matcher Top 5 layout) ---
    c1, c2 = st.columns([1, 1], gap="large")
    
    kategorier_med_pct = {"Afleveringer": ("PASSES", "SUCCESSFULPASSES"), "Dueller": ("DUELS", "DUELSWON")}
    kategorier_uden_pct = {"Mål": "GOALS", "Assists": "ASSISTS", "xG": "XGSHOT", "Skud": "SHOTS", "Minutter": "MINUTESONFIELD"}
    
    tilgaengelige = [k for k in kategorier_med_pct.keys() if kategorier_med_pct[k][0] in df_hif.columns] + \
                   [k for k in kategorier_uden_pct.keys() if kategorier_uden_pct[k] in df_hif.columns]

    with c1:
        valgt_kat = st.pills("Statistik", tilgaengelige, default="Mål", label_visibility="collapsed")
    with c2:
        visning = st.segmented_control("Visning", ["Total", "Pr. 90"], default="Total", label_visibility="collapsed")

    # --- 5. BEREGNING ---
    df_final = df_hif.drop_duplicates()
    min_col = "MINUTESONFIELD"

    if valgt_kat in kategorier_uden_pct:
        col = kategorier_uden_pct[valgt_kat]
        res = df_final.groupby('NAVN', as_index=False).agg({col: 'sum', min_col: 'sum'})
        if res[min_col].max() > 6000: # Sikkerhedscheck for præ-aggregeret data
            res = df_final.groupby('NAVN', as_index=False).agg({col: 'max', min_col: 'max'})
        
        if visning == "Pr. 90" and valgt_kat != "Minutter":
            res['VAL'] = (res[col] / res[min_col] * 90).replace([np.inf, -np.inf], 0).fillna(0)
        else:
            res['VAL'] = res[col]
        res['LABEL'] = res['VAL'].apply(lambda x: f"{x:.2f}" if x % 1 != 0 else f"{int(x)}")
    else:
        tot, suc = kategorier_med_pct[valgt_kat]
        res = df_final.groupby('NAVN', as_index=False).agg({tot: 'sum', suc: 'sum', min_col: 'sum'})
        if res[min_col].max() > 6000:
            res = df_final.groupby('NAVN', as_index=False).agg({tot: 'max', suc: 'max', min_col: 'max'})
        
        pct = (res[suc] / res[tot] * 100).fillna(0)
        if visning == "Pr. 90":
            res['VAL'] = (res[tot] / res[min_col] * 90).replace([np.inf, -np.inf], 0).fillna(0)
            res['LABEL'] = [f"{v:.2f} ({int(p)}%)" for v, p in zip(res['VAL'], pct)]
        else:
            res['VAL'] = res[tot]
            res['LABEL'] = [f"{int(v)} ({int(p)}%)" for v, p in zip(res['VAL'], pct)]

    df_plot = res[res['VAL'] > 0].sort_values('VAL', ascending=False)

    # --- 6. RENDER CUSTOM BARER (HTML) ---
    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
    
    max_val = max(df_plot['VAL'].max(), 1) # Undgå division med 0
    # Skalaen går til 100 eller max_val
    skala = max(100, max_val)

    html_stats = '<div style="background:white; padding:15px; border:1px solid #eee; border-radius:4px;">'
    html_stats += f'<div style="margin-bottom:15px; font-weight:700; font-size:14px; text-transform:uppercase; color:#333; border-bottom:2px solid #df003b; padding-bottom:5px;">{valgt_kat} ({visning})</div>'
    
    for _, r in df_plot.iterrows():
        width = (r['VAL'] / skala) * 100
        html_stats += f"""
            <div class="stat-row">
                <div class="stat-name">{r['NAVN']}</div>
                <div class="stat-bar-container">
                    <div class="stat-bar-fill" style="width: {width}%;"></div>
                </div>
                <div class="stat-value">{r['LABEL']}</div>
            </div>
        """
    html_stats += "</div>"
    
    st.write(html_stats, unsafe_allow_html=True)
