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
        df = pd.read_csv(raw_url)
        df['Dato'] = pd.to_datetime(df['Dato']).dt.date
        
        # --- SØGEFILTRE ØVERST ---
        c1, c2, c3 = st.columns([2, 1, 1])
        
        with c1:
            search_query = st.text_input("Søg spiller/klub", placeholder="Indtast navn...", label_visibility="collapsed")
        
        with c2:
            # Dynamisk liste over positioner i DB
            pos_options = ["Alle positioner"] + sorted(df['Position'].unique().tolist())
            filter_pos = st.selectbox("Position", options=pos_options, label_visibility="collapsed")
            
        with c3:
            # Status filter
            status_options = ["Alle status"] + sorted(df['Status'].unique().tolist())
            filter_status = st.selectbox("Status", options=status_options, label_visibility="collapsed")

        # --- FILTRERING LOGIK ---
        filtered_df = df.copy()
        
        if search_query:
            filtered_df = filtered_df[filtered_df['Navn'].str.contains(search_query, case=False, na=False) | 
                                    filtered_df['Klub'].str.contains(search_query, case=False, na=False)]
        
        if filter_pos != "Alle positioner":
            filtered_df = filtered_df[filtered_df['Position'] == filter_pos]
            
        if filter_status != "Alle status":
            filtered_df = filtered_df[filtered_df['Status'] == filter_status]

        # 2. MASTER-TABEL (Kun nyeste rapport pr. spiller)
        # Vi grupperer efter ID for at undgå dubletter i oversigten
        latest_reports = filtered_df.sort_values('Dato').groupby('ID').tail(1).sort_values('Dato', ascending=False)

        st.markdown(f"<p style='font-size: 12px; color: gray;'>Viser {len(latest_reports)} spillere</p>", unsafe_allow_html=True)
        
        vis_cols = ["Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status"]
        selected_rows = st.dataframe(
            latest_reports[vis_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Rating_Avg": st.column_config.NumberColumn("Rating", format="%.1f"),
                "Dato": st.column_config.DateColumn("Dato")
            }
        )

        # 3. DETALJE-VISNING (Åbner når række vælges)
        if len(selected_rows.selection.rows) > 0:
            idx = selected_rows.selection.rows[0]
            valgt_id = latest_reports.iloc[idx]['ID']
            valgt_navn = latest_reports.iloc[idx]['Navn']
            
            # Hent historik for denne spiller
            spiller_historik = df[df['ID'] == valgt_id].sort_values('Dato', ascending=False)
            
            st.markdown("---")
            st.subheader(f"Profil: {valgt_navn}")
            
            tab1, tab2 = st.tabs(["Seneste Rapport", f"Historik ({len(spiller_historik)})"])
            
            with tab1:
                s = spiller_historik.iloc[0]
                
                # Parametre (1-6)
                st.markdown("**Parametre**")
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
                
                # Tekstbokse
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
                for i, row in spiller_historik.iterrows():
                    with st.expander(f"Rapport: {row['Dato']} | ⭐ {row['Rating_Avg']} | {row['Status']}"):
                        st.write(f"**Vurdering:** {row['Vurdering']}")
                        st.write(f"**Potentiale:** {row['Potentiale']}")

    except Exception as e:
        st.info("Databasen er tom eller kunne ikke hentes.")
