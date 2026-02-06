import streamlit as st
import plotly.express as px
import pandas as pd

def vis_side(spillere, player_events):
    # 1. Rens kolonner
    spillere.columns = [str(c).strip().upper() for c in spillere.columns]
    player_events.columns = [str(c).strip().upper() for c in player_events.columns]

    # 2. De 5 kategorier
    valg_muligheder = {
        "PASSES": "PASSES",
        "SKUD": "SHOTS",
        "DUELLER": "DUELS",
        "EROBRINGER": "RECOVERIES",
        "MINUTTER": "MINUTESTAGGED",
    }
    valgt_label = st.selectbox("Vælg statistik:", list(valg_muligheder.keys()))
    valgt_kolonne = valg_muligheder[valgt_label]

    # 3. Rens ID'er
    spillere['PLAYER_WYID'] = spillere['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    player_events['PLAYER_WYID'] = player_events['PLAYER_WYID'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    # 4. Ordbog til navne
    navne_dict = {}
    for _, row in spillere.iterrows():
        f_name = str(row.get('FIRSTNAME', '')).replace('nan', '')
        l_name = str(row.get('LASTNAME', '')).replace('nan', '')
        navne_dict[str(row['PLAYER_WYID'])] = f"{f_name} {l_name}".strip()

    # 5. Map navne
    player_events['NAVN'] = player_events['PLAYER_WYID'].map(navne_dict).fillna("Ukendt Spiller")

    # 6. Beregn og vis graf
    if valgt_kolonne in player_events.columns:
        df_plot = player_events.groupby('NAVN')[valgt_kolonne].sum().reset_index()
        df_plot = df_plot.sort_values(by=valgt_kolonne, ascending=False).head(15)

        # Vi omdøber kolonnen midlertidigt for at få den rigtige label i boksen
        df_plot = df_plot.rename(columns={valgt_kolonne: valgt_label.capitalize()})
        ny_kolonne_navn = valgt_label.capitalize()

        fig = px.bar(
            df_plot,
            x=ny_kolonne_navn,
            y='NAVN',
            orientation='h',
            text=ny_kolonne_navn,
            color_discrete_sequence=['#df003b'],
            # Dette fjerner "VISNINGSNAVN" og viser de rigtige labels når man holder musen over
            labels={'NAVN': 'Spiller', ny_kolonne_navn: valgt_label.capitalize()}
        )

        # Her skræddersyr vi "svæve-boksen" (hover)
        fig.update_traces(
            hovertemplate="<b>%{y}</b><br>" +
                          valgt_label.capitalize() + ": %{x}<extra></extra>"
        )

        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title=valgt_label.capitalize(),
            yaxis_title="",
            template="plotly_white",
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Kolonnen '{valgt_kolonne}' mangler i Playerevents.")
