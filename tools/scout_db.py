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

        # 3. Den "Lukkede" Tabel (Oversigt)
        vis_cols = ["Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status"]
        st.dataframe(
            filtered_db[vis_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f"),
                "Navn": st.column_config.TextColumn("Navn", width="medium"),
            }
        )

        # 4. "Åbn" spilleren
        # Vi lader brugeren vælge fra de filtrerede navne
        selected_name = st.selectbox(
            "Klik her for at åbne detaljer på en spiller fra tabellen",
            options=["Vælg spiller for at se detaljer..."] + filtered_db['Navn'].tolist()
        )

        if selected_name != "Vælg spiller for at se detaljer...":
            # Hent den valgte spillers data
            s = filtered_db[filtered_db['Navn'] == selected_name].iloc[0]
            
            st.markdown(f"### 📄 Rapport: {s['Navn']}")
            
            # Parametre i 4 kolonner
            st.markdown("**Parametre (1-6)**")
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

            st.markdown("---")
            
            # Kvalitative noter i 3 kolonner med fast bredde
            t1, t2, t3 = st.columns(3)
            with t1:
                st.subheader("💪 Styrker")
                st.info(s['Styrker'] if str(s['Styrker']) != 'nan' else "Ingen noter")
            with t2:
                st.subheader("🛠️ Udvikling")
                st.warning(s['Udvikling'] if str(s['Udvikling']) != 'nan' else "Ingen noter")
            with t3:
                st.subheader("📋 Vurdering")
                st.success(s['Vurdering'] if str(s['Vurdering']) != 'nan' else "Ingen noter")
                
            st.caption(f"Spiller ID: {s['ID']} | Sidst opdateret: {s['Dato']}")

    except Exception as e:
        st.info("Ingen data fundet i systemet.")
