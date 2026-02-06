import streamlit as st
import plotly.express as px
import pandas as pd

def vis_side(spillere, player_events):
    st.title("Spillerstatistik")

    # 1. Mapping af de 5 punkter til dine Excel-kolonner (Tjekket mod dine billeder)
    kategorier = {
        "Minutter": ["MINUTESTAGGED"],
        "Passes": ["PASSES"],
        "Skud": ["SHOTS"],
        "Duels": ["DUELS"],
        "Recoveries": ["RECOVERIES"]
    }

    # 2. Vælg hovedpunkt
    valgt_punkt = st.selectbox("Vælg kategori:", list(kategorier.keys()))

    # 3. Vælg specifik statistik under punktet
    mulige_stats = kategorier[valgt_punkt]
    valgt_stat = st.selectbox(f"Vælg {valgt_punkt}statistik:", mulige_stats)

    # 4. Data-rensning og Merge
    # Tvinger ID til tekst så vi er sikre på de kan finde hinanden
    spillere['PLAYER_WYID'] = spillere['PLAYER_WYID'].astype(str).str.strip()
    player_events['PLAYER_WYID'] = player_events['PLAYER_WYID'].astype(str).str.strip()

    # Vi henter kun de nødvendige navne-kolonner
    df_navne = spillere[['PLAYER_WYID', 'FIRSTNAME', 'LASTNAME']]
    df = player_events.merge(df_navne, on='PLAYER_WYID', how='left')

    # Lav fuldt navn
    df['Full_Name'] = df['FIRSTNAME'].fillna('') + " " + df['LASTNAME'].fillna('')

    # 5. Tjek om kolonnen findes og beregn
    if valgt_stat in df.columns:
        # Hvis det er en PCT (procent) kolonne, tager vi gennemsnittet, ellers summen
        if "PCT" in valgt_stat:
            df_plot = df.groupby('Full_Name')[valgt_stat].mean().reset_index()
        else:
            df_plot = df.groupby('Full_Name')[valgt_stat].sum().reset_index()

        # Sorter og snup top 15
        df_plot = df_plot.sort_values(by=valgt_stat, ascending=False).head(15)

        # 6. Visualisering
        fig = px.bar(
            df_plot,
            x=valgt_stat,
            y='Full_Name',
            orientation='h',
            text=valgt_stat,
            color=valgt_stat,
            color_continuous_scale='Reds' # HIF farver
        )

        fig.update_layout(
            yaxis={'categoryorder':'total ascending'},
            xaxis_title=valgt_stat,
            yaxis_title="",
            margin=dict(l=20, r=20, t=40, b=20),
            height=600,
            template="plotly_white"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error(f"Kolonnen '{valgt_stat}' blev ikke fundet i Playerevents. Tjek om navnet i Excel er stavet præcis sådan.")
