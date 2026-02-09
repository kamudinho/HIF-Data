import streamlit as st
import plotly.express as px
import pandas as pd

def vis_side(spillere, player_events):
    # 1. Rens kolonner
    spillere.columns = [str(c).strip().upper() for c in spillere.columns]
    player_events.columns = [str(c).strip().upper() for c in player_events.columns]

    # 2. Kategorier (Total, Succes)
    kategorier_med_pct = {
        "AFLEVERINGER": ("PASSES", "SUCCESSFULPASSES"),
        "PASSES TO FINAL THIRD": ("PASSESTOFINALTHIRD", "SUCCESSFULPASSESTOFINALTHIRD"),
        "FORWARDPASSES": ("FORWARDPASSES", "SUCCESSFULFORWARDPASSES"),
        "DUELLER": ("DUELS", "DUELSWON"),
    }
    
    # Kategorier med kun ét tal (Ingen successful)
    kategorier_uden_pct = {
        "TOUCHES IN BOX": "TOUCHINBOX",
        "MINUTTER": "MINUTESTAGGED"
    }

    valg_label = st.selectbox("Vælg statistik:", list(kategorier_med_pct.keys()) + list(kategorier_uden_pct.keys()))

    # 3. Rens ID'er
    spillere['PLAYER_WYID'] = spillere['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    player_events['PLAYER_WYID'] = player_events['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # 4. Ordbog til navne
    navne_dict = {}
    for _, row in spillere.iterrows():
        f_name = str(row.get('FIRSTNAME', '')).replace('nan', '')
        l_name = str(row.get('LASTNAME', '')).replace('nan', '')
        navne_dict[str(row['PLAYER_WYID'])] = f"{f_name} {l_name}".strip()

    player_events['NAVN'] = player_events['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # 5. Beregning
    if valg_label in kategorier_uden_pct:
        kolonne = kategorier_uden_pct[valg_label]
        if kolonne in player_events.columns:
            df_plot = player_events.groupby('NAVN')[kolonne].sum().reset_index()
            df_plot = df_plot.sort_values(by=kolonne, ascending=False).head(15)
            # Kun tallet for Touches in Box/Minutter
            df_plot['LABEL'] = df_plot[kolonne].astype(int).astype(str)
            hover_tmpl = "<b>%{y}</b><br>" + valg_label + ": %{x}<extra></extra>"
            custom_data_val = None
        else:
            st.error(f"Kolonnen '{kolonne}' mangler i data.")
            return
    else:
        tot_col, suc_col = kategorier_med_pct[valg_label]
        if tot_col in player_events.columns and suc_col in player_events.columns:
            df_plot = player_events.groupby('NAVN')[[tot_col, suc_col]].sum().reset_index()
            df_plot['PCT'] = (df_plot[suc_col] / df_plot[tot_col] * 100).fillna(0)
            # Tal + Procent for resten
            df_plot['LABEL'] = df_plot.apply(lambda r: f"{int(r[tot_col])} ({r['PCT']:.1f}%)", axis=1)
            df_plot = df_plot.sort_values(by=tot_col, ascending=False).head(15)
            kolonne = tot_col
            hover_tmpl = "<b>%{y}</b><br>Total: %{x}<br>Succes: %{customdata:.1f}%<extra></extra>"
            custom_data_val = df_plot['PCT']
        else:
            st.error(f"Kolonnerne {tot_col} eller {suc_col} mangler i data.")
            return

    # 6. Vis Graf
    fig = px.bar(
        df_plot,
        x=kolonne,
        y='NAVN',
        orientation='h',
        text='LABEL',
        color_discrete_sequence=['#df003b'],
        custom_data=[custom_data_val] if custom_data_val is not None else None,
        labels={'NAVN': 'Spiller', kolonne: valg_label.capitalize()}
    )

    fig.update_traces(
        hovertemplate=hover_tmpl,
        textposition='inside', 
        textfont=dict(color='white')
    )

    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title=valg_label.capitalize(),
        yaxis_title="",
        template="plotly_white",
        height=650
    )

    st.plotly_chart(fig, use_container_width=True)
