import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# Sikrere import af SEASONNAME
try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "2024/2025"

def vis_side(spillere, player_stats_sn):
    # --- 1. LAYOUT INDSTILLINGER ---
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; max-width: 98% !important; }
            .main { background-color: white; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. BRANDING ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem;">SPILLER STATISTIK</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 3. DATA CHECK & PROCESSERING ---
    if player_stats_sn is None or player_stats_sn.empty:
        st.warning("Ingen statistisk data fundet fra Snowflake.")
        return

    s_info = spillere.copy()
    s_stats = player_stats_sn.copy()

    # Tving kolonnenavne til UPPERCASE for konsistens
    s_info.columns = [str(c).upper().strip() for c in s_info.columns]
    s_stats.columns = [str(c).upper().strip() for c in s_stats.columns]

    # Rens PLAYER_WYID
    for df in [s_info, s_stats]:
        if 'PLAYER_WYID' in df.columns:
            df['PLAYER_WYID'] = df['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        else:
            st.error(f"PLAYER_WYID mangler. Fundne kolonner: {list(df.columns)}")
            return

    # Navne-merge
    spillere_clean = s_info.drop_duplicates(subset=['PLAYER_WYID'])
    if 'NAVN' not in spillere_clean.columns and 'FIRSTNAME' in spillere_clean.columns:
        spillere_clean['NAVN'] = (spillere_clean['FIRSTNAME'].fillna('') + " " + spillere_clean['LASTNAME'].fillna('')).str.strip()

    if 'NAVN' not in spillere_clean.columns:
        spillere_clean['NAVN'] = spillere_clean['PLAYER_WYID']

    df_hif = pd.merge(s_stats, spillere_clean[['PLAYER_WYID', 'NAVN']], on='PLAYER_WYID', how='inner')

    if df_hif.empty:
        st.info(f"Ingen spillere matchet i Snowflake for {SEASONNAME}.")
        return

    # --- 4. UI KONTROLLER ---
    # HER ER TILPASNINGEN TIL DE RÅ KOLONNER:
    # Vi bruger XGSHOT og MINUTESONFIELD præcis som de hedder i din liste
    kpi_uden_pct = {
        "Mål": "GOALS", 
        "Assists": "ASSISTS", 
        "xG": "XGSHOT",      # Rettet fra XG
        "Skud": "SHOTS", 
        "Minutter": "MINUTESONFIELD" # Rettet fra MINUTES
    }
    
    kpi_med_pct = {
        "Afleveringer": ("PASSES", "SUCCESSFULPASSES"), 
        "Dueller": ("DUELS", "DUELSWON")
    }
    
    alle_kategorier = list(kpi_uden_pct.keys()) + list(kpi_med_pct.keys())
    
    # Dynamisk tjek om kolonnerne findes i Snowflake-trækket
    tilgaengelige = [k for k in alle_kategorier if 
                    (k in kpi_uden_pct and kpi_uden_pct[k] in df_hif.columns) or 
                    (k in kpi_med_pct and kpi_med_pct[k][0] in df_hif.columns)]

    if not tilgaengelige:
        st.error(f"Ingen af de valgte statistikker blev fundet i Snowflake. Tilgængelige kolonner: {list(df_hif.columns)}")
        return

    c1, c2 = st.columns([1, 1])
    with c1:
        valgt_kat = st.pills("Statistik", tilgaengelige, default=tilgaengelige[0], label_visibility="collapsed")
    with c2:
        sub_c1, sub_c2 = st.columns([1, 1])
        with sub_c2:
            visning = st.segmented_control("Visning", ["Total", "Pr. 90"], default="Total", label_visibility="collapsed")

    # --- 5. BEREGNING AF GRAF-DATA ---
    df_final = df_hif.drop_duplicates()
    min_col = "MINUTESONFIELD" # Kilden til Pr. 90 beregning

    if valgt_kat in kpi_uden_pct:
        stat_col = kpi_uden_pct[valgt_kat]
        res = df_final.groupby('NAVN', as_index=False).agg({stat_col: 'sum', min_col: 'sum'})
        
        if visning == "Pr. 90" and valgt_kat != "Minutter":
            res['VAL'] = (res[stat_col] / res[min_col] * 90).replace([np.inf, -np.inf], 0).fillna(0)
        else:
            res['VAL'] = res[stat_col]
        res['LABEL'] = res['VAL'].apply(lambda x: f"{x:.2f}" if x % 1 != 0 else f"{int(x)}")
    else:
        tot_col, suc_col = kpi_med_pct[valgt_kat]
        res = df_final.groupby('NAVN', as_index=False).agg({tot_col: 'sum', suc_col: 'sum', min_col: 'sum'})
        
        pct = (res[suc_col] / res[tot_col] * 100).fillna(0)
        if visning == "Pr. 90":
            res['VAL'] = (res[tot_col] / res[min_col] * 90).replace([np.inf, -np.inf], 0).fillna(0)
            res['LABEL'] = [f"{v:.2f} ({int(p)}%)" for v, p in zip(res['VAL'], pct)]
        else:
            res['VAL'] = res[tot_col]
            res['LABEL'] = [f"{int(v)} ({int(p)}%)" for v, p in zip(res['VAL'], pct)]

    df_plot = res[res['VAL'] > 0].sort_values('VAL', ascending=True)

    # --- 6. PLOTLY GRAF ---
    h = max(400, (len(df_plot) * 30) + 50)
    fig = px.bar(df_plot, x='VAL', y='NAVN', orientation='h', text='LABEL', labels={'VAL': valgt_kat, 'NAVN': ''})

    fig.update_traces(
        marker_color='#df003b' if visning == "Total" else '#333',
        textposition='outside',
        cliponaxis=False
    )

    fig.update_layout(
        height=h, margin=dict(l=0, r=60, t=10, b=50),
        xaxis=dict(title=dict(text=f"<b>{valgt_kat.upper()}</b> ({visning})", font=dict(size=12)), showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(tickfont=dict(size=12)), plot_bgcolor='white', paper_bgcolor='white'
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
