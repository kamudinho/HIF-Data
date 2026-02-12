import streamlit as st
import pandas as pd
import uuid

# Samme konfiguration som i din input-fil
REPO = "Kamudinho/HIF-data"
FILE_PATH = "scouting_db.csv"

def vis_side():
    st.markdown("<p style='font-size: 18px; font-weight: bold; margin-bottom: 20px;'>Scouting Database</p>", unsafe_allow_html=True)
    
    try:
        # 1. Hent data fra GitHub
        raw_url = f"https://raw.githubusercontent.com/{REPO}/main/{FILE_PATH}?nocache={uuid.uuid4()}"
        df = pd.read_csv(raw_url)
        
        # Konverter dato og sorter
        df['Dato'] = pd.to_datetime(df['Dato']).dt.date
        
        # --- SØGEFILTRE ØVERST ---
        # Vi laver en række med 3 kolonner: Søgefelt (bred), Position (smal), Status (smal)
        filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
        
        with filter_col1:
            search_query = st.text_input("Søg", placeholder="Søg spiller eller klub...", label_visibility="collapsed")
        
        with filter_col2:
            pos_list = ["Alle Positioner"] + sorted(df['Position'].dropna().unique().tolist())
            filter_pos = st.selectbox("Position", options=pos_list, label_visibility="collapsed")
            
        with filter_col3:
            status_list = ["Alle Status"] + sorted(df['Status'].dropna().unique().tolist())
            filter_status = st.selectbox("Status", options=status_list, label_visibility="collapsed")

        # --- FILTRERING LOGIK ---
        f_df = df.copy()
        if search_query:
            f_df = f_df[f_df['Navn'].str.contains(search_query, case=False, na=False) | 
                        f_df['Klub'].str.contains(search_query, case=False, na=False)]
        
        if filter_pos != "Alle Positioner":
            f_df = f_df[f_df['Position'] == filter_pos]
            
        if filter_status != "Alle Status":
            f_df = f_df[f_df['Status'] == filter_status]

        # --- TABELVISNING (Kun nyeste rapport pr. spiller) ---
        # Vi grupperer efter ID og tager den nyeste, så tabellen er ren
        latest_reports = f_df.sort_values('Dato').groupby('ID').tail(1).sort_values('Dato', ascending=False)

        st.markdown(f"<p style='font-size: 12px; color: gray; margin-bottom: 5px;'>Viser {len(latest_reports)} unikke spillere</p>", unsafe_allow_html=True)
        
        # Interaktiv tabel
        vis_cols = ["Dato", "Navn", "Klub", "Position", "Rating_Avg", "Status"]
        event = st.dataframe(
            latest_reports[vis_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Rating_Avg": st.column_config.NumberColumn("⭐ Snit", format="%.1f"),
                "Dato": st.column_config.DateColumn("Senest"),
                "Navn": st.column_config.TextColumn("Navn", width="medium")
            }
        )

        # --- DETALJE-VISNING (Åbner når man klikker på en række) ---
        if len(event.selection.rows) > 0:
            row_idx = event.selection.rows[0]
            valgt_id = latest_reports.iloc[row_idx]['ID']
            valgt_navn = latest_reports.iloc[row_idx]['Navn']
            
            # Find alt historik for denne spiller
            historik = df[df['ID'] == valgt_id].sort_values('Dato', ascending=False)
            
            st.markdown("---")
            st.subheader(f"Spillerprofil: {valgt_navn}")
            
            tab_nyeste, tab_historik = st.tabs(["Seneste Rapport", f"Historik ({len(historik)})"])
            
            with tab_nyeste:
                s = historik.iloc[0]
                
                # Parametre (1-6)
                st.markdown("**Tekniske & Fysiske Stats**")
                p_col1, p_col2, p_col3, p_col4 = st.columns(4)
                p_col1.metric("Beslut.", s['Beslutsomhed'])
                p_col2.metric("Fart", s['Fart'])
                p_col3.metric("Aggres.", s['Aggresivitet'])
                p_col4.metric("Attitude", s['Attitude'])
                
                p_col5, p_col6, p_col7, p_col8 = st.columns(4)
                p_col5.metric("Udhold.", s['Udholdenhed'])
                p_col6.metric("Leder", s['Lederegenskaber'])
                p_col7.metric("Teknik", s['Teknik'])
                p_col8.metric("Intell.", s['Spilintelligens'])

                st.markdown("---")
                
                # Kvalitative noter i 3 bokse
                t_col1, t_col2, t_col3 = st.columns(3)
                with t_col1:
                    st.markdown("**Styrker**")
                    st.info(s['Styrker'] if str(s['Styrker']) != 'nan' else "-")
                with t_col2:
                    st.markdown("**Udvikling**")
                    st.warning(s['Udvikling'] if str(s['Udvikling']) != 'nan' else "-")
                with t_col3:
                    st.markdown("**Vurdering**")
                    st.success(s['Vurdering'] if str(s['Vurdering']) != 'nan' else "-")
                
                st.caption(f"ID: {s['ID']} | Potentiale: {s['Potentiale']}")

            with tab_historik:
                for i, row in historik.iterrows():
                    with st.expander(f"Rapport fra {row['Dato']} | Snit: {row['Rating_Avg']}"):
                        st.write(f"**Vurdering:** {row['Vurdering']}")
                        st.write(f"**Klub på det tidspunkt:** {row['Klub']}")

    except Exception:
        st.info("💡 Databasen er tom. Gå til 'Input' for at oprette din første scoutingrapport.")
