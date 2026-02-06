import streamlit as st
import plotly.express as px


def vis_side(spillere):

    kategorier = {
        "Mål": "GOALS",
        "Assists": "ASSIST",
        "Minutter spillet": "MINUTESONFIELD",
        "xG (Expected Goals)": "XGSHOT"
    }

    valgt_label = st.selectbox("Vælg kategori:", list(kategorier.keys()))
    valgt_kolonne = kategorier[valgt_label]

    # 2. Sorter data og snup top 15
    df_plot = spillere.sort_values(by=valgt_kolonne, ascending=False).head(15)

    # 3. Lav grafen (Plotly gør den interaktiv)
    fig = px.bar(
        df_plot,
        x=valgt_kolonne,
        y="Spiller",  # Navnet på kolonnen med spillernavne
        orientation='h',
        text=valgt_kolonne,
        color_discrete_sequence=['#0056a3']  # Hvidovre blå (eller rød #df003b)
    )

    # Gør designet rent og pænt
    fig.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title=valgt_label,
        yaxis_title="",
        template="plotly_white",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)
