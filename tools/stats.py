import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# Forsøg at hente SEASONNAME fra din data-fil
try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "Aktuel Sæson"

def vis_side(spillere, player_stats_sn):
    # --- 0. CSS TIL TOTAL KANT-TIL-KANT FLEX OG FEJLRETNING ---
    st.markdown("""
        <style>
            /* Fjern standard Streamlit margener */
            .block-container {
                padding-top: 1rem !important;
                padding-bottom: 0rem !important;
                max-width: 98% !important;
            }
            
            /* Tving kolonne-layoutet til at bruge hele bredden */
            [data-testid="stHorizontalBlock"] {
                width: 100% !important;
                gap: 0px !important;
            }

            /* Tving specifikt den højre kolonne (c2) til at skubbe indholdet helt ud til kanten */
            [data-testid="column"]:nth-of-type(2) [data-testid="stVerticalBlock"] {
                align-items: flex-end !important;
            }

            /* Højrestil Segmented Control */
            div[data-testid="stSegmentedControl"] {
                display: flex !important;
                justify-content: flex-end !important;
                width: fit-content !important;
                margin-left: auto !important;
            }
            
            /* Gør Pills mere kompakte */
            div[data-testid="stPills"] {
                width: 100% !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. RENT DESIGN (HIF BRANDING) ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem;">SPILLERSTATISTIK</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 2. DATA KLARGØRING ---
    spillere.columns = [str(c).upper().strip() for c in spillere.columns]
    player_stats_sn.columns = [str(c).upper().strip() for c in player_stats_sn.columns]

    # ID Match Fix
    spillere['PLAYER_WYID'] = spillere['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    player_stats_sn['PLAYER_WYID'] = player_stats_sn['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # Filtrer på SEASONNAME (Nu er variablen sikret i toppen)
    if 'SEASONNAME' in player_stats_sn.columns:
        df_stats = player_stats_sn[player_stats_sn['SEASONNAME'] == SEASONNAME].copy()
    else:
        df_stats = player_stats_sn.copy()

    # Rens dubletter i spillertabellen
    spillere_clean = spillere.drop_duplicates(subset=['PLAYER_WYID'])
    if 'NAVN' not in spillere_clean.columns:
        spillere_clean['NAVN'] = (spillere_clean['FIRSTNAME'].fillna('') + " " + spillere_clean['LASTNAME'].fillna('')).str.strip()

    # Merge
    df_hif = pd.merge(df_stats, spillere_clean[['PLAYER_WYID', 'NAVN']], on='PLAYER_WYID', how='inner')

    if df_hif.empty:
        st.info(f"Ingen data fundet for {SEASONNAME}")
        return

    # --- 3. UI KONTROLLER ---
    # Vi giver c1 mere plads (2 units) og c2 mindre plads (1 unit) for at hjælpe med højrestillingen
    c1, c2 = st.columns([2, 1])
    
    kategorier_med_pct = {
        "Afleveringer": ("PASSES", "SUCCESSFULPASSES"),
        "Dueller": ("DUELS", "DUELSWON"),
    }
    kategorier_uden_pct = {
        "Mål": "GOALS", "Assists": "ASSISTS", "xG": "XGSHOT", 
        "Afslutninger": "SHOTS", "Minutter": "MINUTESONFIELD"
    }

    tilgaengelige = [k for k in kategorier_med_pct.keys() if kategorier_med_pct[k][0] in df_hif.columns] + \
                   [k for k in kategorier_uden_pct.keys() if kategorier_uden_pct[k] in df_hif.columns]

    with c1:
        valg_label = st.pills("Statistik", tilgaengelige, default="Mål", label_visibility="collapsed")
    with c2:
        # Denne tvinges nu helt til højre af CSS 'margin-left: auto'
        visning = st.segmented_control("Visning", ["Total", "Pr. 90"], default="Total", label_visibility="collapsed")

    # --- 4. BEREGNING ---
    min_col = "MINUTESONFIELD"
    df_final = df_hif.drop_duplicates()

    if valg_label in kategorier_uden_pct:
        kolonne = kategorier_uden_pct[valg_label]
        df_group = df_final.groupby('NAVN', as_index=False).agg({kolonne: 'sum', min_col: 'sum'})
        if df_group[min_col].max() > 6000:
            df_group = df_final.groupby('NAVN', as_index=False).agg({kolonne: 'max', min_col: 'max'})
        if visning == "Pr. 90" and valg_label != "Minutter":
            df_group['VAL'] = np.where(df_group[min_col] > 0, (df_group[kolonne] / df_group[min_col] * 90), 0)
        else:
            df_group['VAL'] = df_group[kolonne]
        df_group['LABEL'] = df_group['VAL'].apply(lambda x: f"{x:.2f}" if x % 1 != 0 else f"{int(x)}")
    else:
        tot_col, suc_col = kategorier_med_pct[valg_label]
        df_group = df_final.groupby('NAVN', as_index=False).agg({tot_col: 'sum', suc_col: 'sum', min_col: 'sum'})
        if df_group[min_col].max() > 6000:
            df_group = df_final.groupby('NAVN', as_index=False).agg({tot_col: 'max', suc_col: 'max', min_col: 'max'})
        df_group['PCT'] = (df_group[suc_col] / df_group[tot_col] * 100).fillna(0)
        if visning == "Pr. 90":
            df_group['VAL'] = np.where(df_group[min_col] > 0, (df_group[tot_col] / df_group[min_col] * 90), 0)
            df_group['LABEL'] = df_group.apply(lambda r: f"{r['VAL']:.2f} ({int(r['PCT'])}%)", axis=1)
        else:
            df_group['VAL'] = df_group[tot_col]
            df_group['LABEL'] = df_group.apply(lambda r: f"{int(r['VAL'])} ({int(r['PCT'])}%)", axis=1)

    df_plot = df_group[df_group['VAL'] > 0].sort_values(by='VAL', ascending=True)

    # --- 5. GRAF ---
    st.markdown("<div style='margin-bottom:5px;'></div>", unsafe_allow_html=True)
    calc_height = max(400, (len(df_plot) * 32) + 60)
    bar_color = '#df003b' if visning == "Total" else '#333'
    
    fig = px.bar(df_plot, x='VAL', y='NAVN', orientation='h', text='LABEL')
    fig.update_traces(marker_color=bar_color, textposition='outside', cliponaxis=False, textfont_size=12)
    fig.update_layout(
        height=calc_height,
        margin=dict(l=0, r=60, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0', showticklabels=False),
        yaxis=dict(tickfont_size=12, title="", automargin=True),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
