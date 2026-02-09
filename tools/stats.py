import streamlit as st
import plotly.express as px
import pandas as pd

def vis_side(spillere, player_events):
    # 1. Rens kolonner
    spillere.columns = [str(c).strip().upper() for c in spillere.columns]
    player_events.columns = [str(c).strip().upper() for c in player_events.columns]

    # 2. Kategorier (Vi linker den totale kolonne med den succesfulde)
    kategorier = {
        "AFLEVERINGER": ("PASSES", "SUCCESSFUL_PASSES"),
        "SKUD": ("SHOTS", "SUCCESSFUL_SHOTS"),
        "DUELLER": ("DUELS", "SUCCESSFUL_DUELS"),
        "EROBRINGER": ("RECOVERIES", "SUCCESSFUL_RECOVERIES"),
    }
    
    # Tilføj minutter separat da de ikke har en succes-rate
    valg_label = st.selectbox("Vælg statistik:", list(kategorier.keys()) + ["MINUTTER"])

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
    if valg_label == "MINUTTER":
        kolonne = "MINUTESTAGGED"
        df_plot = player_events.groupby('NAVN')[kolonne].sum().reset_index()
        df_plot = df_plot.sort_values(by=kolonne, ascending=False).head(15)
        df_plot['LABEL'] = df_plot[kolonne].astype(str)
        hover_tmpl = "<b>%{y}</b><br>Minutter: %{x}<extra></extra>"
    else:
        tot_col, suc_col = kategorier[valg_label]
        
        if tot_col in player_events.columns and suc_col in player_events.columns:
            # Gruppér og opsummer
            df_plot = player_events.groupby('NAVN')[[tot_col, suc_col]].sum().reset_index()
            
            # Beregn procent (håndter division med nul)
            df_plot['PCT'] = (df_plot[suc_col] / df_plot[tot_col] * 100).fillna(0)
            
            # Lav den ønskede tekst-label: "150 (85%)"
            df_plot['LABEL'] = df_plot.apply(lambda r: f"{int(r[tot_col])} ({r['PCT']:.1f}%)", axis=1)
            
            df_plot = df_plot.sort_values(by=tot_col, ascending=False).head(15)
            kolonne = tot_col
            hover_tmpl = "<b>%{y}</b><br>Total: %{x}<br>Succes: %{customdata}%<extra></extra>"
        else:
            st.error(f"Kolonnerne {tot_col} eller {suc_col} mangler i data.")
            return

    # 6. Vis Graf
    fig = px.bar(
        df_plot,
        x=kolonne,
        y='NAVN',
        orientation='h',
        text='LABEL', # Her viser vi "xxx (xx%)"
        color_discrete_sequence=['#df003b'],
        custom_data=['PCT'] if valg_label != "MINUTTER" else None,
        labels={'NAVN': 'Spiller', kolonne: valg_label.capitalize()}
    )

    fig.update_traces(
        hovertemplate=hover_tmpl,
        textposition='outside' # Sætter teksten for enden af søjlen
    )

    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title=valg_label.capitalize(),
        yaxis_title="",
        template="plotly_white",
        height=650,
        margin=dict(r=50) # Ekstra plads til de lange labels
    )

    st.plotly_chart(fig, use_container_width=True)
