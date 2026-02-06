import streamlit as st
import plotly.express as px

def vis_side(spillere, player_events):

    # 1. Vi fletter (merger) de to ark sammen vha. PLAYER_WYID
    # Det gør, at vi får FIRSTNAME/LASTNAME over på vores stats-rækker
    df = player_events.merge(
        spillere[['PLAYER_WYID', 'FIRSTNAME', 'LASTNAME']], 
        on='PLAYER_WYID', 
        how='left'
    )

    # 2. Lav fuldt navn
    df['Full_Name'] = df['FIRSTNAME'] + " " + df['LASTNAME']

    # 3. Find alle talkolonner (stats)
    talkolonner = df.select_dtypes(include=['number']).columns.tolist()
    
    # Fjern tekniske ID-kolonner fra listen, så de ikke driller i dropdown
    relevante_stats = [col for col in talkolonner if col not in ['PLAYER_WYID', 'TEAM_WYID', 'WYID']]

    # 4. Dropdown til valg af kategori
    valgt_kolonne = st.selectbox("Vælg statistik-kategori:", relevante_stats)

    # 5. Gruppér data (Hvis en spiller optræder flere gange, lægger vi deres stats sammen)
    df_grouped = df.groupby('Full_Name')[valgt_kolonne].sum().reset_index()

    # 6. Sorter og snup top 15
    df_plot = df_grouped.sort_values(by=valgt_kolonne, ascending=False).head(15)

    # 7. Lav grafen
    fig = px.bar(
        df_plot,
        x=valgt_kolonne,
        y='Full_Name',
        orientation='h',
        text=valgt_kolonne,
        color_discrete_sequence=['#df003b'] # Hvidovre rød
    )

    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        xaxis_title=valgt_kolonne,
        yaxis_title="",
        height=600,
        template="plotly_white"
    )

    st.plotly_chart(fig, use_container_width=True)
