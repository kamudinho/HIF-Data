import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "Aktuel Sæson"

def vis_side(spillere, player_stats_sn):
    # --- 1. RENT DESIGN (HIF BRANDING) ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:25px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem;">SPILLER STATISTIK</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # 2. Rens & Klargør Data
    spillere.columns = [str(c).strip().upper() for c in spillere.columns]
    player_stats_sn.columns = [str(c).strip().upper() for c in player_stats_sn.columns]

    # Sæsonvælger (Kompakt)
    if 'SEASONNAME' in player_stats_sn.columns:
        saesoner = sorted(player_stats_sn['SEASONNAME'].unique(), reverse=True)
        valgt_saeson = st.selectbox("Sæson", saesoner, label_visibility="collapsed")
        df_stats = player_stats_sn[player_stats_sn['SEASONNAME'] == valgt_saeson].copy()
    else:
        df_stats = player_stats_sn.copy()

    # ID Match Fix
    spillere['PLAYER_WYID'] = spillere['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_stats['PLAYER_WYID'] = df_stats['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    if 'NAVN' not in spillere.columns:
        spillere['NAVN'] = (spillere['FIRSTNAME'].fillna('') + " " + spillere['LASTNAME'].fillna('')).str.strip()

    df_hif = pd.merge(df_stats, spillere[['PLAYER_WYID', 'NAVN']], on='PLAYER_WYID', how='inner')

    if df_hif.empty:
        st.info("Ingen data fundet.")
        return

    # --- 3. UI KONTROLLER (Samme stil som Top 5) ---
    c1, c2 = st.columns([1, 1], gap="large")
    
    kategorier_med_pct = {
        "Afleveringer": ("PASSES", "SUCCESSFULPASSES"),
        "Dueller": ("DUELS", "DUELSWON"),
    }
    kategorier_uden_pct = {
        "Mål": "GOALS",
        "Assists": "ASSISTS",
        "xG": "XGSHOT",
        "Afslutninger": "SHOTS",
        "Minutter": "MINUTESONFIELD"
    }

    tilgaengelige = [k for k, v in kategorier_med_pct.items() if v[0] in df_hif.columns] + \
                   [k for k, v in kategorier_uden_pct.items() if v in df_hif.columns]

    with c1:
        valg_label = st.pills("Statistik", tilgaengelige, default="Mål", label_visibility="collapsed")
    with c2:
        st.markdown('<div style="display: flex; justify-content: flex-end;">', unsafe_allow_html=True)
        visning = st.segmented_control("Visning", ["Total", "Pr. 90"], default="Total", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

   # --- 4. BEREGNING (RETTET) ---
    min_col = "MINUTESONFIELD"
    
    # 1. FIX: Fjern dubletter før vi summerer. 
    # Vi antager, at en unik kombination af spillernavn, minutter og mål pr. række er nok til at spotte en dublet.
    # Hvis du har et MATCHID eller en unik DATE i dit Snowflake-træk, så tilføj den til subset herunder.
    df_unique = df_hif.drop_duplicates(subset=['PLAYER_WYID', 'NAVN', 'MINUTESONFIELD', 'GOALS', 'ASSISTS'])

    if valg_label in kategorier_uden_pct:
        kolonne = kategorier_uden_pct[valg_label]
        # Vi summerer på det rensede datasæt
        df_group = df_unique.groupby('NAVN', as_index=False).agg({kolonne: 'sum', min_col: 'sum'})
        
        if visning == "Pr. 90" and valg_label != "Minutter":
            df_group['VAL'] = np.where(df_group[min_col] > 0, (df_group[kolonne] / df_group[min_col] * 90), 0)
        else:
            df_group['VAL'] = df_group[kolonne]
        df_group['LABEL'] = df_group['VAL'].apply(lambda x: f"{x:.2f}" if x % 1 != 0 else f"{int(x)}")
    
    else:
        tot_col, suc_col = kategorier_med_pct[valg_label]
        # Vi summerer på det rensede datasæt
        df_group = df_unique.groupby('NAVN', as_index=False).agg({tot_col: 'sum', suc_col: 'sum', min_col: 'sum'})
        
        df_group['PCT'] = (df_group[suc_col] / df_group[tot_col] * 100).fillna(0)
        if visning == "Pr. 90":
            df_group['VAL'] = np.where(df_group[min_col] > 0, (df_group[tot_col] / df_group[min_col] * 90), 0)
            df_group['LABEL'] = df_group.apply(lambda r: f"{r['VAL']:.2f} ({int(r['PCT'])}%)", axis=1)
        else:
            df_group['VAL'] = df_group[tot_col]
            df_group['LABEL'] = df_group.apply(lambda r: f"{int(r['VAL'])} ({int(r['PCT'])}%)", axis=1)

    df_plot = df_group[df_group['VAL'] > 0].sort_values(by='VAL', ascending=True)

    # --- 5. GRAF (Clean Design) ---
    st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
    
    # Farvevalg baseret på visning (HIF Rød eller Neutral Grå/Blå)
    bar_color = '#df003b' if visning == "Total" else '#333'

    fig = px.bar(
        df_plot, 
        x='VAL', 
        y='NAVN', 
        orientation='h', 
        text='LABEL',
        labels={'NAVN': '', 'VAL': ''}
    )

    fig.update_traces(
        marker_color=bar_color,
        textposition='outside',
        cliponaxis=False,
        textfont_size=12,
        hovertemplate='%{y}: <b>%{text}</b><extra></extra>'
    )

    fig.update_layout(
        height=40 + (len(df_plot) * 30), # Dynamisk højde baseret på antal spillere
        margin=dict(l=0, r=50, t=0, b=0),
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0', showticklabels=False),
        yaxis=dict(autorange="reversed", tickfont_size=13),
        plot_bgcolor='white',
        paper_bgcolor='white',
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
