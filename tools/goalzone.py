import streamlit as st
import pandas as pd

def vis_side(df_events, df_spillere, hold_map):
    # 1. Rens kolonner i BEGGE ark med det samme
    df_events.columns = [str(c).strip().upper() for c in df_events.columns]
    df_spillere.columns = [str(c).strip().upper() for c in df_spillere.columns]

    # 2. Lav navne-opslaget (Sørg for at PLAYER_WYID findes)
    # Vi bruger .get() for at undgå KeyError hvis en række mangler data
    navne_dict = {}
    for _, row in df_spillere.iterrows():
        pid = str(row.get('PLAYER_WYID', '')).split('.')[0] # Fjerner .0
        f = str(row.get('FIRSTNAME', '')).replace('nan', '')
        l = str(row.get('LASTNAME', '')).replace('nan', '')
        navne_dict[pid] = f"{f} {l}".strip()

    # 3. Tilføj NAVN til events
    df_events['PLAYER_ID_STR'] = df_events['PLAYER_WYID'].astype(str).str.split('.').str[0]
    df_events['NAVN'] = df_events['PLAYER_ID_STR'].map(navne_dict).fillna("Ukendt")

    # Nu kan du fortsætte med din zone-logik...
    st.write("Data er nu koblet korrekt!")
    st.write(df_events[['NAVN', 'PRIMARYTYPE']].head())
