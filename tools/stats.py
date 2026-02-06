import streamlit as st
import plotly.express as px

def vis_side(spillere):

    # 1. Vi finder alle talkolonner i dit ark (f.eks. GOALS, ASSISTS, SHOTS)
    talkolonner = spillere.select_dtypes(include=['number']).columns.tolist()
    
    # 2. Vi bygger spillernavnet ved at samle FIRSTNAME og LASTNAME
    if "FIRSTNAME" in spillere.columns and "LASTNAME" in spillere.columns:
        spillere['Full_Name'] = spillere['FIRSTNAME'] + " " + spillere['LASTNAME']
        navne_kolonne = 'Full_Name'
    else:
        # Fallback hvis navnene ikke findes som forventet
        navne_kolonne = spillere.columns[1] 

    # 3. Fjern kolonner der ikke giver mening at lave statistik på (f.eks. PLAYER_WYID eller BIRTHDATE)
    relevante_stats = [col for col in talkolonner if col not in ['PLAYER_WYID', 'BIRTHDATE']]

    # 4. Brugeren vælger kategori
    valgt_kolonne = st.selectbox("Vælg statistik-kategori:", relevante_stats)

    # 5. Sortering (Top 15)
    df_plot = spillere.sort_values(by=valgt_kolonne, ascending=False).head(15)

    # 6. Lav grafen (Plotly)
    fig = px.bar(
        df_plot,
        x=valgt_kolonne,
        y=navne_kolonne,
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
