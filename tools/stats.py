import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# Sikrere import af SEASONNAME
try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "Aktuel Sæson"

def vis_side(spillere, player_stats_sn):
    # --- 1. LAYOUT INDSTILLINGER ---
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; max-width: 98% !important; }
            /* Gør titlen i Plotly grafer mindre for at matche tabeller */
            .main { background-color: white; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. BRANDING (Identisk med Top 5) ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem;">SPILLER STATISTIK</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 3. DATA PROCESSERING ---
    s_info = spillere.copy()
    s_stats = player_stats_sn.copy()
    s_info.columns = [str(c).upper().strip() for c in s_info.columns]
    s_stats.columns = [str(c).upper().strip() for c in s_stats.columns]

    # VIGTIGT: Rens ID'er for at sikre match
    s_info['PLAYER_WYID'] = s_info['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    s_stats['PLAYER_WYID'] = s_stats['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # Sæson-filter
    if 'SEASONNAME' in s_stats.columns:
        df_stats = s_stats[s_stats['SEASONNAME'] == SEASONNAME].copy()
    else:
        df_stats = s_stats.copy()

    # Navne-merge
    spillere_clean = s_info.drop_duplicates(subset=['PLAYER_WYID'])
    if 'NAVN' not in spillere_clean.columns:
        spillere_clean['NAVN'] = (spillere_clean['FIRSTNAME'].fillna('') + " " + spillere_clean['LASTNAME'].fillna('')).str.strip()

    df_hif = pd.merge(df_stats, spillere_clean[['PLAYER_WYID', 'NAVN']], on='PLAYER_WYID', how='inner')

    if df_hif.empty:
        st.warning("Ingen data fundet for denne sæson.")
        return

    # --- 4. UI KONTROLLER (Præcis centrering) ---
    c1, c2 = st.columns([1, 1])
    
    kpi_uden_pct = {"Mål": "GOALS", "Assists": "ASSISTS", "xG": "XGSHOT", "Skud": "SHOTS", "Minutter": "MINUTESONFIELD"}
    kpi_med_pct = {"Afleveringer": ("PASSES", "SUCCESSFULPASSES"), "Dueller": ("DUELS", "DUELSWON")}
    
    alle_kategorier = list(kpi_uden_pct.keys()) + list(kpi_med_pct.keys())
    tilgaengelige = [k for k in alle_kategorier if (k in kpi_uden_pct and kpi_uden_pct[k] in df_hif.columns) or (k in kpi_med_pct and kpi_med_pct[k][0] in df_hif.columns)]

    with c1:
        valgt_kat = st.pills("Statistik", tilgaengelige, default="Mål", label_visibility="collapsed")
    with c2:
        # Tvinger Segmented Control helt til højre via en række indvendige columns
        sub_c1, sub_c2 = st.columns([1, 1])
        with sub_c2:
            visning = st.segmented_control("Visning", ["Total", "Pr. 90"], default="Total", label_visibility="collapsed")

    # --- 5. BEREGNING AF GRAF-DATA ---
    df_final = df_hif.drop_duplicates()
    min_col = "MINUTESONFIELD"

    if valgt_kat in kpi_uden_pct:
        stat_col = kpi_uden_pct[valgt_kat]
        res = df_final.groupby('NAVN', as_index=False).agg({stat_col: 'sum', min_col: 'sum'})
        if res[min_col].max() > 6000: res = df_final.groupby('NAVN', as_index=False).agg({stat_col: 'max', min_col: 'max'})
        
        if visning == "Pr. 90" and valgt_kat != "Minutter":
            res['VAL'] = (res[stat_col] / res[min_col] * 90).replace([np.inf, -np.inf], 0).fillna(0)
        else:
            res['VAL'] = res[stat_col]
        res['LABEL'] = res['VAL'].apply(lambda x: f"{x:.2f}" if x % 1 != 0 else f"{int(x)}")
    else:
        tot_col, suc_col = kpi_med_pct[valgt_kat]
        res = df_final.groupby('NAVN', as_index=False).agg({tot_col: 'sum', suc_col: 'sum', min_col: 'sum'})
        if res[min_col].max() > 6000: res = df_final.groupby('NAVN', as_index=False).agg({tot_col: 'max', suc_col: 'max', min_col: 'max'})
        
        pct = (res[suc_col] / res[tot_col] * 100).fillna(0)
        if visning == "Pr. 90":
            res['VAL'] = (res[tot_col] / res[min_col] * 90).replace([np.inf, -np.inf], 0).fillna(0)
            res['LABEL'] = [f"{v:.2f} ({int(p)}%)" for v, p in zip(res['VAL'], pct)]
        else:
            res['VAL'] = res[tot_col]
            res['LABEL'] = [f"{int(v)} ({int(p)}%)" for v, p in zip(res['VAL'], pct)]

    df_plot = res[res['VAL'] > 0].sort_values('VAL', ascending=True)

   # --- 6. PLOTLY GRAF (Størst øverst + kategori-label) ---
    st.markdown("<div style='margin-bottom:10px;'></div>", unsafe_allow_html=True)
    
    # Sortering: Vi sorterer dataframe, så de mindste værdier er først 
    # (Plotly tegner nemlig nedefra og op på y-aksen)
    df_plot = df_plot.sort_values('VAL', ascending=True)
    
    h = max(400, (len(df_plot) * 30) + 50)
    
    fig = px.bar(
        df_plot, 
        x='VAL', 
        y='NAVN', 
        orientation='h', 
        text='LABEL',
        labels={'VAL': valgt_kat, 'NAVN': ''}
    )

    fig.update_traces(
        marker_color='#df003b' if visning == "Total" else '#333',
        textposition='outside',
        cliponaxis=False
    )

    fig.update_layout(
        height=h,
        margin=dict(l=0, r=60, t=10, b=50),
        xaxis=dict(
            title=dict(
                text=f"<b>{valgt_kat.upper()}</b> ({visning})", 
                font=dict(size=12, color='#333')
            ),
            showgrid=True,
            gridcolor='#f0f0f0'
        ),
        yaxis=dict(
            tickfont=dict(size=12),
            # Fjern 'reversed' herfra, da vi nu sorterer i selve dataframen
            autorange=True 
        ),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
