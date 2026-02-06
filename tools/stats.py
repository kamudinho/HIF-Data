import streamlit as st
import plotly.express as px

def vis_side(spillere):

    # 1. Find alle kolonner der indeholder tal (Mål, Assists, xG osv.)
    talkolonner = spillere.select_dtypes(include=['number']).columns.tolist()
    
    # 2. Find kolonnen med navne (vi tjekker de mest sandsynlige navne)
    mulige_navne = ["Player", "Spiller", "Navn", "player", "spiller"]
    navne_kolonne = None
    
    for kol i mulige_navne:
        if kol in spillere.columns:
            navne_kolonne = kol
            break
            
    # Fejlhåndtering hvis data ikke matcher
    if not talkolonner:
        st.error("Kunne ikke finde nogen talkolonner i dit Excel-ark.")
        return
    if not navne_kolonne:
        st.error(f"Kunne ikke finde navne-kolonnen. Kolonner i Excel: {spillere.columns.tolist()}")
        return

    # 3. Brugeren vælger kategori direkte fra dine Excel-overskrifter
    valgt_kolonne = st.selectbox("Vælg statistik:", talkolonner)

    # 4. Sorter og plot
    df_plot = spillere.sort_values(by=valgt_kolonne, ascending=False).head(15)

    fig = px.bar(
        df_plot,
        x=valgt_kolonne,
        y=navne_kolonne,
        orientation='h',
        text=valgt_kolonne,
        color_discrete_sequence=['#df003b'] # Hvidovre Rød
    )

    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        xaxis_title=valgt_kolonne,
        yaxis_title="",
        margin=dict(l=20, r=20, t=20, b=20),
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)
