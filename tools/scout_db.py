import streamlit as st
import pandas as pd
import uuid

REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

def vis_side():
    st.markdown("<p style='font-size: 16px; font-weight: bold;'>Scouting Database</p>", unsafe_allow_html=True)
    
    try:
        # Hent data
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db = pd.read_csv(raw_url)
        
        # Sørg for at datoen er sorteret rigtigt (nyeste først)
        db['Dato'] = pd.to_datetime(db['Dato']).dt.date
        db = db.sort_values(by='Dato', ascending=False)

        # --- SØGEFELT ---
        search_query = st.text_input("Søg efter spiller, klub eller position", placeholder="Indtast navn...")

        # Filtrering af data baseret på søgning
        if search_query:
            filtered_db = db[
                db['Navn'].str.contains(search_query, case=False, na=False) |
                db['Klub'].str.contains(search_query, case=False, na=False) |
                db['Position'].str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered_db = db

        # --- OVERSIGT (KUN BASIS INFO) ---
        # Vi viser kun de overordnede informationer i oversigten
        st.markdown("---")
        
        if filtered_db.empty:
            st.warning("Ingen spillere fundet.")
        else:
            # Visning af hver spiller i en expander (det aktive valg)
            for _, spiller in filtered_db.iterrows():
                # Overskrift for expander med Navn, Rating (Avg) og Status
                header = f"{spiller['Navn']} | {spiller['Klub']} | {spiller['Position']} | ⭐ {spiller['Rating_Avg']} | {spiller['Status']}"
                
                with st.expander(header):
                    # Detaljeret visning når man trykker
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Dato:** {spiller['Dato']}")
                        st.write(f"**Potentiale:** {spiller['Potentiale']}")
                        st.write(f"**ID:** {spiller['ID']}")
                    
                    # Parametre i 4 kolonner (ligesom i input)
                    st.markdown("**Parametre (1-6)**")
                    p1, p2, p3, p4 = st.columns(4)
                    p1.metric("Beslut.", spiller['Beslutsomhed'])
                    p2.metric("Fart", spiller['Fart'])
                    p3.metric("Aggres.", spiller['Aggresivitet'])
                    p4.metric("Attitude", spiller['Attitude'])
                    
                    p5, p6, p7, p8 = st.columns(4)
                    p5.metric("Udhold.", spiller['Udholdenhed'])
                    p6.metric("Leder", spiller['Lederegenskaber'])
                    p7.metric("Teknik", spiller['Teknik'])
                    p8.metric("Intell.", spiller['Spilintelligens'])
                    
                    st.markdown("---")
                    
                    # Tekstbokse med fast bredde og automatisk højde
                    t1, t2, t3 = st.columns(3)
                    with t1:
                        st.markdown("**Styrker**")
                        st.info(spiller['Styrker'] if str(spiller['Styrker']) != 'nan' else "-")
                    with t2:
                        st.markdown("**Udvikling**")
                        st.warning(spiller['Udvikling'] if str(spiller['Udvikling']) != 'nan' else "-")
                    with t3:
                        st.markdown("**Vurdering**")
                        st.success(spiller['Vurdering'] if str(spiller['Vurdering']) != 'nan' else "-")

    except Exception as e:
        st.info("Databasen er tom eller kunne ikke hentes.")
        # st.error(e) # Fjern kommentar for fejlfinding
