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

        # 2. Søgefelt (Søger i Navn, Klub og Position)
        search_query = st.text_input("Søg i databasen", placeholder="Søg på spiller, klub eller position...")
        
        if search_query:
            filtered_db = db[
                db['Navn'].str.contains(search_query, case=False, na=False) |
                db['Klub'].str.contains(search_query, case=False, na=False) |
                db['Position'].str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered_db = db

        # 3. Tabeloversigt (Kun basisdata)
        # Vi definerer de kolonner, der skal vises i selve tabellen
        vis_cols = ["Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status", "Potentiale"]
        
        # Tabel-konfiguration for at gøre det pænt
        st.dataframe(
            filtered_db[vis_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rating_Avg": st.column_config.NumberColumn("⭐ Rating", format="%.1f"),
                "Dato": st.column_config.DateColumn("Dato"),
                "Navn": st.column_config.TextColumn("Navn", width="medium"),
            }
        )

        st.markdown("---")
        st.markdown("<p style='font-size: 14px; font-weight: bold;'>Vælg spiller for at se detaljer og noter:</p>", unsafe_allow_html=True)

        # 4. Detalje-vælger (Aktivt valg)
        valgt_spiller_navn = st.selectbox("Vælg spiller fra listen for at folde rapporten ud", 
                                          options=["Vælg spiller..."] + filtered_db['Navn'].tolist(),
                                          label_visibility="collapsed")

        if valgt_spiller_navn != "Vælg spiller...":
            # Find data for den valgte spiller (tager den nyeste hvis der er dubletter)
            spiller = filtered_db[filtered_db['Navn'] == valgt_spiller_navn].iloc[0]
            
            # --- VISNING AF DETALJER ---
            st.info(f"**Rapport for {spiller['Navn']}** ({spiller['ID']})")
            
            # Parametre i 4 kolonner
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

            # Tekstbokse (Styrker, Udvikling, Vurdering)
            st.markdown("---")
            t1, t2, t3 = st.columns(3)
            with t1:
                st.markdown("**Styrker**")
                st.help(spiller['Styrker']) # Bruger help eller markdown for pæn visning
            with t2:
                st.markdown("**Udvikling**")
                st.help(spiller['Udvikling'])
            with t3:
                st.markdown("**Vurdering**")
                st.help(spiller['Vurdering'])

    except Exception as e:
        st.info("Databasen er tom eller kunne ikke indlæses.")
