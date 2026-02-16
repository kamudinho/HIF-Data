import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

def vis_side(spillere, player_stats_sn):

    # 1. Rens kolonner
    spillere.columns = [str(c).strip().upper() for c in spillere.columns]
    # Snowflake data skal have SEASONNAME eller SEASON_WYID tilgængelig
    player_stats_sn.columns = [str(c).strip().upper() for c in player_stats_sn.columns]

    # 2. Sæsonvælger (NYT)
    # Vi antager at din SQL i data_load nu henter SEASONNAME. 
    # Hvis ikke, så tjek din q_playerstats i data_load.py
    if 'SEASONNAME' in player_stats_sn.columns:
        saesoner = sorted(player_stats_sn['SEASONNAME'].unique(), reverse=True)
        valgt_saeson = st.selectbox("Vælg Sæson:", saesoner)
        # Filtrér Snowflake data med det samme
        df_stats_saeson = player_stats_sn[player_stats_sn['SEASONNAME'] == valgt_saeson].copy()
    else:
        st.warning("SEASONNAME kolonne ikke fundet. Viser alt data.")
        df_stats_saeson = player_stats_sn.copy()

    # 3. UI - Statistikvalg
    c1, c2 = st.columns([2, 1])
    with c1:
        kategorier_med_pct = {
            "AFLEVERINGER": ("PASSES", "SUCCESSFULPASSES"),
            "DUELLER": ("DUELS", "DUELSWON"),
        }
        kategorier_uden_pct = {
            "MÅL": "GOALS",
            "ASSISTS": "ASSISTS",
            "XG": "XGSHOT",
            "AFSLUTNINGER": "SHOTS",
            "MINUTTER": "MINUTESONFIELD"
        }
        
        tilgaengelige_med = [k for k, v in kategorier_med_pct.items() if v[0] in df_stats_saeson.columns]
        tilgaengelige_uden = [k for k, v in kategorier_uden_pct.items() if v in df_stats_saeson.columns]
        valg_label = st.selectbox("Vælg statistik:", tilgaengelige_med + tilgaengelige_uden)

    with c2:
        visning = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)

    # --- 4. MERGE & BEREGNING ---
    spillere['PLAYER_WYID'] = spillere['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_stats_saeson['PLAYER_WYID'] = df_stats_saeson['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    if 'NAVN' not in spillere.columns:
        spillere['NAVN'] = (spillere['FIRSTNAME'].fillna('') + " " + spillere['LASTNAME'].fillna('')).str.strip()

    df_hif = pd.merge(df_stats_saeson, spillere[['PLAYER_WYID', 'NAVN']], on='PLAYER_WYID', how='inner')

    if df_hif.empty:
        st.info(f"Ingen data fundet for sæsonen: {valgt_saeson}")
        return

    # Resten af beregningslogikken (Identisk med din tidligere, men nu på df_hif som er filtreret)
    df_plot = pd.DataFrame()
    min_col = "MINUTESONFIELD"

    if valg_label in kategorier_uden_pct:
        kolonne = kategorier_uden_pct[valg_label]
        df_group = df_hif.groupby('NAVN', as_index=False).agg({kolonne: 'sum', min_col: 'sum'})
        if visning == "Pr. 90" and valg_label != "MINUTTER":
            df_group['VAL'] = np.where(df_group[min_col] > 0, (df_group[kolonne] / df_group[min_col] * 90), 0)
            df_group['LABEL'] = df_group['VAL'].map('{:.2f}'.format)
        else:
            df_group['VAL'] = df_group[kolonne]
            df_group['LABEL'] = df_group['VAL'].apply(lambda x: f"{x:.2f}" if isinstance(x, float) else str(int(x)))
        df_plot = df_group.sort_values(by='VAL', ascending=False)
    else:
        tot_col, suc_col = kategorier_med_pct[valg_label]
        df_group = df_hif.groupby('NAVN', as_index=False).agg({tot_col: 'sum', suc_col: 'sum', min_col: 'sum'})
        df_group['PCT'] = (df_group[suc_col] / df_group[tot_col] * 100).fillna(0)
        if visning == "Pr. 90":
            df_group['VAL'] = np.where(df_group[min_col] > 0, (df_group[tot_col] / df_group[min_col] * 90), 0)
            df_group['LABEL'] = df_group.apply(lambda r: f"{r['VAL']:.2f} ({r['PCT']:.1f}%)", axis=1)
        else:
            df_group['VAL'] = df_group[tot_col]
            df_group['LABEL'] = df_group.apply(lambda r: f"{int(r['VAL'])} ({r['PCT']:.1f}%)", axis=1)
        df_plot = df_group.sort_values(by='VAL', ascending=False)

    # --- 5. GRAF ---
    fig = px.bar(df_plot, x='VAL', y='NAVN', orientation='h', text='LABEL',
                 color_discrete_sequence=['#df003b' if visning == "Total" else '#0056b3'],
                 labels={'NAVN': '', 'VAL': f"{valg_label} ({visning})"})
    fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=700, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
