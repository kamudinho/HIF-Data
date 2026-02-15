import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

def vis_side(spillere, player_events):
    # 1. Rens kolonner og fjern specialtegn/mellemrum
    spillere.columns = [str(c).strip().upper().replace(" ", "") for c in spillere.columns]
    player_events.columns = [str(c).strip().upper().replace(" ", "") for c in player_events.columns]

    # 2. UI - Valgmuligheder
    c1, c2 = st.columns([2, 1])
    with c1:
        # Tjek dine kolonnenavne i CSV'en – de skal matche disse præcis!
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

    # 3. Rens ID'er og Map Navne
    spillere['PLAYER_WYID'] = spillere['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    player_events['PLAYER_WYID'] = player_events['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    navne_dict = {}
    for _, row in spillere.iterrows():
        f_name = str(row.get('FIRSTNAME', '')).replace('nan', '')
        l_name = str(row.get('LASTNAME', '')).replace('nan', '')
        navne_dict[str(row['PLAYER_WYID'])] = f"{f_name} {l_name}".strip()

    player_events['NAVN'] = player_events['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # --- 4. Beregning med Fejltjek (Her var fejlen) ---
    df_plot = pd.DataFrame()
    
    # Lav en liste over tilgængelige kolonner for at undgå KeyError
    cols_in_data = player_events.columns.tolist()

    if valg_label in kategorier_uden_pct:
        kolonne = kategorier_uden_pct[valg_label]
        
        if kolonne not in cols_in_data:
            st.error(f"Kolonnen '{kolonne}' blev ikke fundet i dataen. Tilgængelige kolonner: {cols_in_data}")
            return

        df_group = player_events.groupby('NAVN').agg({kolonne: 'sum', 'MINUTESTAGGED': 'sum'}).reset_index()
        # ... (resten af din logik for uden pct)
        if visning == "Pr. 90" and valg_label != "MINUTTER":
            df_group['VAL'] = np.where(df_group['MINUTESTAGGED'] > 0, (df_group[kolonne] / df_group['MINUTESTAGGED'] * 90), 0)
            df_group['LABEL'] = df_group['VAL'].map('{:.2f}'.format)
        else:
            df_group['VAL'] = df_group[kolonne]
            df_group['LABEL'] = df_group['VAL'].astype(int).astype(str)
            
        df_plot = df_group.sort_values(by='VAL', ascending=False).head(15)
        hover_tmpl = "<b>%{y}</b><br>" + visning + ": %{x}<extra></extra>"
        custom_data_val = None

    else:
        tot_col, suc_col = kategorier_med_pct[valg_label]
        
        # TJEK OM KOLONNERNE FINDES
        missing = [c for c in [tot_col, suc_col, 'MINUTESTAGGED'] if c not in cols_in_data]
        if missing:
            st.error(f"Følgende kolonner mangler i din CSV: {missing}")
            with st.expander("Se alle fundne kolonnenavne"):
                st.write(cols_in_data)
            return

        df_group = player_events.groupby('NAVN').agg({tot_col: 'sum', suc_col: 'sum', 'MINUTESTAGGED': 'sum'}).reset_index()
        
        df_group['PCT'] = (df_group[suc_col] / df_group[tot_col] * 100).fillna(0)
        
        if visning == "Pr. 90":
            df_group['VAL'] = np.where(df_group['MINUTESTAGGED'] > 0, (df_group[tot_col] / df_group['MINUTESTAGGED'] * 90), 0)
            df_group['LABEL'] = df_group.apply(lambda r: f"{r['VAL']:.2f} ({r['PCT']:.1f}%)", axis=1)
        else:
            df_group['VAL'] = df_group[tot_col]
            df_group['LABEL'] = df_group.apply(lambda r: f"{int(r['VAL'])} ({r['PCT']:.1f}%)", axis=1)
            
        df_plot = df_group.sort_values(by='VAL', ascending=False).head(15)
        hover_tmpl = "<b>%{y}</b><br>"+visning+": %{x:.2f}<br>Succes: %{customdata:.1f}%<extra></extra>"
        custom_data_val = df_plot['PCT']

    # 5. Vis Graf (Forbliver den samme)
    if not df_plot.empty:
        fig = px.bar(
            df_plot, x='VAL', y='NAVN', orientation='h', text='LABEL',
            color_discrete_sequence=[BAR_COLOR],
            custom_data=[custom_data_val] if custom_data_val is not None else None,
            labels={'NAVN': 'Spiller', 'VAL': f"{valg_label} ({visning})"}
        )
        # ... (update_traces og update_layout som før)
        st.plotly_chart(fig, use_container_width=True)
