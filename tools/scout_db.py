import streamlit as st
import pandas as pd
import uuid

REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

def vis_side():
    st.markdown("<p style='font-size: 16px; font-weight: bold;'>Scouting Database</p>", unsafe_allow_html=True)
    
    try:
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        df = pd.read_csv(raw_url)
        df['Dato'] = pd.to_datetime(df['Dato']).dt.date
        
        # 1. SØGEFELT
        search_query = st.text_input("🔍 Søg i databasen", placeholder="Navn, klub eller position...")
        if search_query:
            df = df[df['Navn'].str.contains(search_query, case=False, na=False) | 
                    df['Klub'].str.contains(search_query, case=False, na=False)]

        # 2. UNIK SPILLER-OVERSIGT (Viser kun den nyeste rapport pr. spiller i tabellen)
        # Vi grupperer efter ID og tager den nyeste dato
        latest_reports = df.sort_values('Dato').groupby('ID').tail(1).sort_values('Dato', ascending=False)

        st.markdown("**Seneste rapporter pr. spiller**")
        
        # Vi bruger st.dataframe til det hurtige overblik
        vis_cols = ["Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status"]
        selected_rows = st.dataframe(
            latest_reports[vis_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun", # Gør det muligt at vælge rækken direkte (Streamlit 1.35+)
            selection_mode="single-row",
            column_config={"Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f")}
        )

        # 3. DETALJE-VISNING (Hvis en række vælges)
        if len(selected_rows.selection.rows) > 0:
            idx = selected_rows.selection.rows[0]
            valgt_id = latest_reports.iloc[idx]['ID']
            valgt_navn = latest_reports.iloc[idx]['Navn']
            
            # Hent alle rapporter på denne specifikke spiller
            spiller_historik = df[df['ID'] == valgt_id].sort_values('Dato', ascending=False)
            
            st.markdown(f"---")
            st.markdown(f"### 🛡️ Spillerprofil: {valgt_navn}")
            
            # Faner: Nyeste rapport vs. Historik
            tab1, tab2 = st.tabs(["Seneste Vurdering", f"Historik ({len(spiller_historik)} rapporter)"])
            
            with tab1:
                s = spiller_historik.iloc[0] # Den nyeste
                
                # Parametre
                st.markdown("**Parametre (1-6)**")
                p1, p2, p3, p4 = st.columns(4)
                p1.metric("Beslut.", s['Beslutsomhed'])
                p2.metric("Fart", s['Fart'])
                p3.metric("Aggres.", s['Aggresivitet'])
                p4.metric("Attitude", s['Attitude'])
                
                p5, p6, p7, p8 = st.columns(4)
                p5.metric("Udhold.", s['Udholdenhed'])
                p6.metric("Leder", s['Lederegenskaber'])
                p7.metric("Teknik", s['Teknik'])
                p8.metric("Intell.", s['Spilintelligens'])

                st.markdown("---")
                # Tekstbokse med automatisk højde (info/warning/success)
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

            with tab2:
                # Vis en simpel liste over gamle rapporter
                for i, row in spiller_historik.iterrows():
                    with st.expander(f"Rapport fra {row['Dato']} - Rating: {row['Rating_Avg']} ({row['Status']})"):
                        st.write(f"**Vurdering:** {row['Vurdering']}")
                        st.write(f"**Potentiale:** {row['Potentiale']}")

    except Exception as e:
        st.info("Søg efter en spiller eller vælg en række for at se detaljer.")
