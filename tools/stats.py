import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

def vis_side(spillere, player_stats_sn):
    """
    spillere: df_players_gh (fra GitHub)
    player_stats_sn: df_playerstats (fra Snowflake)
    """
    st.title("📊 Spillerstatistik (Snowflake)")

    # 1. Rens kolonner for at undgå whitespace/case fejl
    spillere.columns = [str(c).strip().upper() for c in spillere.columns]
    player_stats_sn.columns = [str(c).strip().upper() for c in player_stats_sn.columns]

    # 2. UI - Valgmuligheder (Tilpasset Snowflake kolonnenavne)
    c1, c2 = st.columns([2, 1])
    with c1:
        # Her parrer vi label med (Total-kolonne, Succes-kolonne) fra Snowflake
        kategorier_med_pct = {
            "AFLEVERINGER": ("PASSES", "SUCCESSFULPASSES"),
            "PROGRESSIVE PASSES": ("PROGRESSIVEPASSES", "SUCCESSFULPROGRESSIVEPASSES"), # Hvis de findes
            "DUELLER": ("DUELS", "DUELSWON"),
        }
        kategorier_uden_pct = {
            "MÅL": "GOALS",
            "ASSISTS": "ASSISTS",
            "XG (Expected Goals)": "XGSHOT",
            "AFSLUTNINGER": "SHOTS",
            "MINUTTER": "MINUTESONFIELD"
        }
        
        # Filtrer kategorier der faktisk findes i dine Snowflake data
        tilgaengelige_med = [k for k, v in kategorier_med_pct.items() if v[0] in player_stats_sn.columns]
        tilgaengelige_uden = [k for k, v in kategorier_uden_pct.items() if v in player_stats_sn.columns]
        
        valg_label = st.selectbox("Vælg statistik:", tilgaengelige_med + tilgaengelige_uden)

    with c2:
        visning = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)

    BAR_COLOR = '#df003b' if visning == "Total" else '#0056b3'

    # --- 3. Rens ID'er og MERGE ---
    # Sikr os at ID'er er strenge (Strings)
    spillere['PLAYER_WYID'] = spillere['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    player_stats_sn['PLAYER_WYID'] = player_stats_sn['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # Opret NAVN i spillere-filen
    if 'NAVN' not in spillere.columns:
        spillere['NAVN'] = (spillere['FIRSTNAME'].fillna('') + " " + spillere['LASTNAME'].fillna('')).str.strip()

    # Merge Snowflake-statistik med din trup-liste
    df_hif = pd.merge(
        player_stats_sn, 
        spillere[['PLAYER_WYID', 'NAVN']], 
        on='PLAYER_WYID', 
        how='inner' 
    )

    if df_hif.empty:
        st.warning("Kunne ikke matche Snowflake-data med spillerlisten. Tjek PLAYER_WYID.")
        return

    # --- 4. BEREGNING ---
    df_plot = pd.DataFrame()
    
    # Minutter kolonne navn (Snowflake bruger typisk MINUTESONFIELD)
    min_col = "MINUTESONFIELD"

    if valg_label in kategorier_uden_pct:
        kolonne = kategorier_uden_pct[valg_label]
        
        df_group = df_hif.groupby('NAVN', as_index=False).agg({
            kolonne: 'sum', 
            min_col: 'sum'
        })
        
        if visning == "Pr. 90" and valg_label != "MINUTTER":
            df_group['VAL'] = np.where(df_group[min_col] > 0, (df_group[kolonne] / df_group[min_col] * 90), 0)
            df_group['LABEL'] = df_group['VAL'].map('{:.2f}'.format)
        else:
            df_group['VAL'] = df_group[kolonne]
            df_group['LABEL'] = df_group['VAL'].apply(lambda x: f"{x:.2f}" if isinstance(x, float) else str(int(x)))
            
        df_plot = df_group.sort_values(by='VAL', ascending=False).head(20) # Top 20 for overskuelighed
        hover_tmpl = "<b>%{y}</b><br>" + visning + ": %{x}<extra></extra>"
        custom_data_val = None

    else:
        tot_col, suc_col = kategorier_med_pct[valg_label]
        
        df_group = df_hif.groupby('NAVN', as_index=False).agg({
            tot_col: 'sum', 
            suc_col: 'sum', 
            min_col: 'sum'
        })
        
        df_group['PCT'] = (df_group[suc_col] / df_group[tot_col] * 100).fillna(0)
        
        if visning == "Pr. 90":
            df_group['VAL'] = np.where(df_group[min_col] > 0, (df_group[tot_col] / df_group[min_col] * 90), 0)
            df_group['LABEL'] = df_group.apply(lambda r: f"{r['VAL']:.2f} ({r['PCT']:.1f}%)", axis=1)
        else:
            df_group['VAL'] = df_group[tot_col]
            df_group['LABEL'] = df_group.apply(lambda r: f"{int(r['VAL'])} ({r['PCT']:.1f}%)", axis=1)
            
        df_plot = df_group.sort_values(by='VAL', ascending=False).head(20)
        hover_tmpl = "<b>%{y}</b><br>"+visning+": %{x:.2f}<br>Succes: %{customdata:.1f}%<extra></extra>"
        custom_data_val = df_plot['PCT']

    # --- 5. VIS GRAF ---
    if not df_plot.empty:
        fig = px.bar(
            df_plot, 
            x='VAL', 
            y='NAVN', 
            orientation='h', 
            text='LABEL',
            color_discrete_sequence=[BAR_COLOR],
            custom_data=[custom_data_val] if custom_data_val is not None else None,
            labels={'NAVN': '', 'VAL': f"{valg_label} ({visning})"}
        )
        
        fig.update_traces(
            hovertemplate=hover_tmpl,
            textposition='auto', 
            textfont=dict(size=12),
            cliponaxis=False 
        )
        
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending', 'tickfont': dict(size=13)},
            xaxis_title=f"{valg_label} - {visning}",
            template="plotly_white",
            height=700,
            margin=dict(r=80, l=0)
        )
        
        st.plotly_chart(fig, use_container_width=True)
