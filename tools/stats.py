import streamlit as st
import plotly.express as px
import pandas as pd

def vis_side(spillere, player_events):
    st.title("📊 Spillerstatistik")

    # 1. Tjek om PLAYER_WYID findes i begge ark - ellers kan vi ikke merge
    if 'PLAYER_WYID' not in spillere.columns or 'PLAYER_WYID' not in player_events.columns:
        st.error(f"Fejl: 'PLAYER_WYID' mangler i et af arkene. Fundet i Spillere: {'PLAYER_WYID' in spillere.columns}, Fundet i Playerevents: {'PLAYER_WYID' in player_events.columns}")
        return

    # 2. Find de rigtige kolonnenavne til fornavn og efternavn (uanset om det er store eller små bogstaver)
    f_name_col = next((c for c in spillere.columns if c.upper() == 'FIRSTNAME'), None)
    l_name_col = next((c for c in spillere.columns if c.upper() == 'LASTNAME'), None)

    if not f_name_col or not l_name_col:
        st.error(f"Kunne ikke finde navne-kolonner. De findes som: {spillere.columns.tolist()}")
        return

    # 3. Vi fletter arkene sammen
    df = player_events.merge(
        spillere[['PLAYER_WYID', f_name_col, l_name_col]], 
        on='PLAYER_WYID', 
        how='left'
    )

    # 4. Lav fuldt navn
    df['Full_Name'] = df[f_name_col].fillna('') + " " + df[l_name_col].fillna('')

    # 5. Find alle talkolonner (stats) og fjern de tekniske
    talkolonner = df.select_dtypes(include=['number']).columns.tolist()
    tekniske_id = ['PLAYER_WYID', 'TEAM_WYID', 'WYID', 'BIRTHDATE', 'ID']
    relevante_stats = [col for col in talkolonner if col.upper() not in tekniske_id]

    # 6. Dropdown til valg af kategori
    valgt_kolonne = st.selectbox("Vælg statistik:", relevante_stats)

    # 7. Gruppér og sortér (læg data sammen hvis en spiller har flere rækker)
    df_grouped = df.groupby('Full_Name')[valgt_kolonne].sum().reset_index()
    df_plot = df_grouped.sort_values(by=valgt_kolonne, ascending=False).head(15)

    # 8. Lav grafen
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
