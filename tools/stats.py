import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

def vis_side(spillere, player_events):
    # 1. Rens kolonner
    spillere.columns = [str(c).strip().upper().replace(" ", "") for c in spillere.columns]
    player_events.columns = [str(c).strip().upper().replace(" ", "") for c in player_events.columns]

    # 2. UI - Valgmuligheder
    c1, c2 = st.columns([2, 1])
    with c1:
        kategorier_med_pct = {
            "AFLEVERINGER": ("PASSES", "SUCCESSFULPASSES"),
            "PASSES TO FINAL THIRD": ("PASSESTOFINALTHIRD", "SUCCESSFULPASSESTOFINALTHIRD"),
            "FORWARD PASSES": ("FORWARDPASSES", "SUCCESSFULFORWARDPASSES"),
            "DUELLER": ("DUELS", "DUELSWON"),
        }
        kategorier_uden_pct = {
            "TOUCHES IN BOX": "TOUCHINBOX",
            "MINUTTER": "MINUTESTAGGED"
        }
        valg_label = st.selectbox("Vælg statistik:", list(kategorier_med_pct.keys()) + list(kategorier_uden_pct.keys()))

    with c2:
        visning = st.radio("Visning", ["Total", "Pr. 90"], horizontal=True)

    BAR_COLOR = '#df003b' if visning == "Total" else '#0056b3'

   # --- 3. Rens ID'er og FILTRERING (KUN HVIDOVRE) ---
    # Sikr os at ID'er er strenge og uden .0
    spillere['PLAYER_WYID'] = spillere['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    player_events['PLAYER_WYID'] = player_events['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # Opret NAVN i spillere-filen hvis den ikke findes
    if 'NAVN' not in spillere.columns:
        spillere['NAVN'] = (spillere['FIRSTNAME'].fillna('') + " " + spillere['LASTNAME'].fillna('')).str.strip()

    # VIGTIGT: Vi laver en kopi af truppen med kun de to nødvendige kolonner
    truppen = spillere[['PLAYER_WYID', 'NAVN']].copy()

    # Merge player_events med truppen
    # Vi bruger 'left' join her for at fejlsøge, og filtrerer bagefter
    df_hif = pd.merge(
        player_events, 
        truppen, 
        on='PLAYER_WYID', 
        how='inner'  # Beholder kun de spillere der findes i din spillere-fil
    )

    # Tjek om vi overhovedet har data tilbage efter merge
    if df_hif.empty:
        st.warning("Ingen match fundet mellem statistikker og spillerlisten. Tjek om PLAYER_WYID findes i begge filer.")
        return

    # --- 4. Beregning ---
    df_plot = pd.DataFrame()

    if valg_label in kategorier_uden_pct:
        kolonne = kategorier_uden_pct[valg_label]
        
        # Vi grupperer på 'NAVN' (som vi lige har flettet ind fra spillere-filen)
        df_group = df_hif.groupby('NAVN', as_index=False).agg({
            kolonne: 'sum', 
            'MINUTESTAGGED': 'sum'
        })
        
        if visning == "Pr. 90" and valg_label != "MINUTTER":
            df_group['VAL'] = np.where(df_group['MINUTESTAGGED'] > 0, (df_group[kolonne] / df_group['MINUTESTAGGED'] * 90), 0)
            df_group['LABEL'] = df_group['VAL'].map('{:.2f}'.format)
        else:
            df_group['VAL'] = df_group[kolonne]
            df_group['LABEL'] = df_group['VAL'].astype(int).astype(str)
            
        df_plot = df_group.sort_values(by='VAL', ascending=False)
        hover_tmpl = "<b>%{y}</b><br>" + visning + ": %{x}<extra></extra>"
        custom_data_val = None

    else:
        tot_col, suc_col = kategorier_med_pct[valg_label]
        
        # Beregn pr. række før vi grupperer (mere sikkert)
        df_group = df_hif.groupby('NAVN', as_index=False).agg({
            tot_col: 'sum', 
            suc_col: 'sum', 
            'MINUTESTAGGED': 'sum'
        })
        
        df_group['PCT'] = (df_group[suc_col] / df_group[tot_col] * 100).fillna(0)
        
        if visning == "Pr. 90":
            df_group['VAL'] = np.where(df_group['MINUTESTAGGED'] > 0, (df_group[tot_col] / df_group['MINUTESTAGGED'] * 90), 0)
            df_group['LABEL'] = df_group.apply(lambda r: f"{r['VAL']:.2f} ({r['PCT']:.1f}%)", axis=1)
        else:
            df_group['VAL'] = df_group[tot_col]
            df_group['LABEL'] = df_group.apply(lambda r: f"{int(r['VAL'])} ({r['PCT']:.1f}%)", axis=1)
            
        df_plot = df_group.sort_values(by='VAL', ascending=False)
        hover_tmpl = "<b>%{y}</b><br>"+visning+": %{x:.2f}<br>Succes: %{customdata:.1f}%<extra></extra>"
        custom_data_val = df_plot['PCT']

    # --- 4. Beregning med Fejltjek ---
    df_plot = pd.DataFrame()
    cols_in_data = df_hif.columns.tolist()

    if valg_label in kategorier_uden_pct:
        kolonne = kategorier_uden_pct[valg_label]
        if kolonne not in cols_in_data:
            st.error(f"Kolonnen '{kolonne}' mangler.")
            return

        df_group = df_hif.groupby('NAVN').agg({kolonne: 'sum', 'MINUTESTAGGED': 'sum'}).reset_index()
        
        if visning == "Pr. 90" and valg_label != "MINUTTER":
            df_group['VAL'] = np.where(df_group['MINUTESTAGGED'] > 0, (df_group[kolonne] / df_group['MINUTESTAGGED'] * 90), 0)
            df_group['LABEL'] = df_group['VAL'].map('{:.2f}'.format)
        else:
            df_group['VAL'] = df_group[kolonne]
            df_group['LABEL'] = df_group['VAL'].astype(int).astype(str)
            
        df_plot = df_group.sort_values(by='VAL', ascending=False)
        hover_tmpl = "<b>%{y}</b><br>" + visning + ": %{x}<extra></extra>"
        custom_data_val = None

    else:
        tot_col, suc_col = kategorier_med_pct[valg_label]
        missing = [c for c in [tot_col, suc_col, 'MINUTESTAGGED'] if c not in cols_in_data]
        if missing:
            st.error(f"Mangler: {missing}")
            return

        df_group = df_hif.groupby('NAVN').agg({tot_col: 'sum', suc_col: 'sum', 'MINUTESTAGGED': 'sum'}).reset_index()
        df_group['PCT'] = (df_group[suc_col] / df_group[tot_col] * 100).fillna(0)
        
        if visning == "Pr. 90":
            df_group['VAL'] = np.where(df_group['MINUTESTAGGED'] > 0, (df_group[tot_col] / df_group['MINUTESTAGGED'] * 90), 0)
            df_group['LABEL'] = df_group.apply(lambda r: f"{r['VAL']:.2f} ({r['PCT']:.1f}%)", axis=1)
        else:
            df_group['VAL'] = df_group[tot_col]
            df_group['LABEL'] = df_group.apply(lambda r: f"{int(r['VAL'])} ({r['PCT']:.1f}%)", axis=1)
            
        df_plot = df_group.sort_values(by='VAL', ascending=False)
        hover_tmpl = "<b>%{y}</b><br>"+visning+": %{x:.2f}<br>Succes: %{customdata:.1f}%<extra></extra>"
        custom_data_val = df_plot['PCT']

   # 5. Vis Graf
    if not df_plot.empty:
        fig = px.bar(
            df_plot, 
            x='VAL', 
            y='NAVN', 
            orientation='h', 
            text='LABEL',
            color_discrete_sequence=[BAR_COLOR],
            custom_data=[custom_data_val] if custom_data_val is not None else None,
            labels={'NAVN': 'Spiller', 'VAL': f"{valg_label} ({visning})"}
        )
        
        fig.update_traces(
            hovertemplate=hover_tmpl,
            # 'auto' placerer tekst udenfor hvis baren er for lille
            textposition='auto', 
            # Styr skriftstørrelsen her (insidetextanchor sikrer tekst starter fra bunden af baren)
            textfont=dict(size=12, color='black'), 
            insidetextfont=dict(color='white'), # Hvid tekst når den er INDE i baren
            cliponaxis=False # Sikrer at tekst uden for baren ikke klippes
        )
        
        fig.update_layout(
            yaxis={
                'categoryorder': 'total ascending',
                'tickfont': dict(size=14) # HER tilpasses skriftstørrelsen på navnene
            },
            xaxis_title=f"{valg_label.capitalize()} - {visning}",
            yaxis_title="",
            template="plotly_white",
            height=max(750, len(df_plot) * 35), # Lidt mere plads pr. række
            margin=dict(r=80) # Giver plads i højre side til tekst uden for barerne
        )
        
        st.plotly_chart(fig, use_container_width=True)
