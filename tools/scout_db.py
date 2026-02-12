import streamlit as st
import pandas as pd
import uuid

REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

def vis_side():
    st.markdown("<p style='font-size: 16px; font-weight: bold;'>Scouting Database</p>", unsafe_allow_html=True)
    
    try:
        # 1. Hent data
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        db = pd.read_csv(raw_url)
        
        # Sorter efter nyeste dato
        db['Dato'] = pd.to_datetime(db['Dato']).dt.date
        db = db.sort_values(by='Dato', ascending=False)

        # 2. Søgefelt
        search_query = st.text_input("🔍 Søg i databasen", placeholder="Navn, klub eller position...")
        
        if search_query:
            filtered_db = db[
                db['Navn'].str.contains(search_query, case=False, na=False) |
                db['Klub'].str.contains(search_query, case=False, na=False) |
                db['Position'].str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered_db = db

        # 3. Den "Foldbare" Tabel
        # Vi laver en header-række for at det ligner en tabel
        h1, h2, h3, h4, h5 = st.columns([2, 1, 1, 1, 1])
        h1.markdown("**Navn**")
        h2.markdown("**Klub**")
        h3.markdown("**Pos**")
        h4.markdown("**Rating**")
        h5.markdown("**Status**")
        st.markdown("---")

        if filtered_db.empty:
            st.info("Ingen spillere fundet.")
        else:
            for _, s in filtered_db.iterrows():
                # Her skaber vi "rækken" som en expander
                # Vi formaterer titlen så den ligner en tabelrække
                titel = f"{s['Navn'].ljust(20)} | {s['Klub']} | {s['Position']} | ⭐ {s['Rating_Avg']} | {s['Status']}"
                
                with st.expander(titel):
                    # --- INDHOLDET NÅR MAN ÅBNER ---
                    st.markdown(f"**Detaljeret rapport for {s['Navn']}** (ID: {s['ID']})")
                    
                    # Parametre i 4 kolonner
                    st.write("---")
                    p1, p2, p3, p4 = st.columns(4)
                    p1.metric("Beslutsomhed", s['Beslutsomhed'])
                    p2.metric("Fart", s['Fart'])
                    p3.metric("Aggresivitet", s['Aggresivitet'])
                    p4.metric("Attitude", s['Attitude'])
                    
                    p5, p6, p7, p8 = st.columns(4)
                    p5.metric("Udholdenhed", s['Udholdenhed'])
                    p6.metric("Leder", s['Lederegenskaber'])
                    p7.metric("Teknik", s['Teknik'])
                    p8.metric("Intelligens", s['Spilintelligens'])

                    st.write("---")
                    
                    # Tekstbokse i 3 kolonner (Styrker, Udvikling, Vurdering)
                    t1, t2, t3 = st.columns(3)
                    with t1:
                        st.markdown("**Styrker**")
                        st.info(s['Styrker'] if str(s['Styrker']) != 'nan' else "-")
                    with t2:
                        st.markdown("**Udvikling**")
                        st.warning(s['Udvikling'] if str(s['Udvikling']) != 'nan' else "-")
                    with t3:
                        st.markdown("**Vurdering**")
                        st.success(s['Vurdering'] if str(s['Vurdering']) != 'nan' else "-")
                    
                    st.caption(f"Rapport dato: {s['Dato']} | Potentiale: {s['Potentiale']}")

    except Exception as e:
        st.info("Ingen data fundet.")
