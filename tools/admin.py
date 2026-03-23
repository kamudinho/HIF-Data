import streamlit as st
import pandas as pd
import uuid

def vis_log():
    """Viser systemets aktivitetslog med filtre placeret over tabellen."""
    aktuel_rolle = str(st.session_state.get("role", "")).lower()
    
    if aktuel_rolle != "admin":
        st.error("Adgang nægtet.")
        return

    st.write("### System Log")
    
    try:
        # Cache-busting for at hente nyeste data
        url = f"https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/action_log.csv?nocache={uuid.uuid4()}"
        df_log = pd.read_csv(url)
        
        # 1. Rens kolonnenavne (fjerner eventuelle mellemrum fra CSV-filen)
        df_log.columns = [c.strip() for c in df_log.columns]
        
        # 2. Konverter datoer korrekt
        df_log['Dato'] = pd.to_datetime(df_log['Dato']).dt.date
        
        # --- FILTRE ØVERST ---
        st.markdown("#### Filtre")
        f1, f2, f3, f4 = st.columns(4)
        
        with f1:
            brugere = ["Alle"] + sorted(df_log['Bruger'].unique().astype(str).tolist())
            valgt_bruger = st.selectbox("Bruger", brugere)
            
        with f2:
            handlinger = ["Alle"] + sorted(df_log['Handling'].unique().astype(str).tolist())
            valgt_handling = st.selectbox("Handling", handlinger)
            
        with f3:
            # Vi tjekker om kolonnen 'Mål' findes, ellers fejler appen
            if 'Mål' in df_log.columns:
                maal_list = ["Alle"] + sorted(df_log['Mål'].unique().astype(str).tolist())
            else:
                maal_list = ["Alle (Kolonne mangler)"]
            valgt_maal = st.selectbox("Mål", maal_list)
            
        with f4:
            min_d = df_log['Dato'].min()
            max_d = df_log['Dato'].max()
            # VIGTIGT: Vi gemmer valget
            valgt_dato = st.date_input("Dato-interval", [min_d, max_d])

        # --- ANVEND FILTRERING ---
        query = pd.Series([True] * len(df_log))
        
        if valgt_bruger != "Alle":
            query &= (df_log['Bruger'] == valgt_bruger)
        
        if valgt_handling != "Alle":
            query &= (df_log['Handling'] == valgt_handling)

        if valgt_maal != "Alle":
            query &= (df_log['Mål'] == valgt_maal)
            
        # SIKKER DATO-FILTRERING: Tjek om vi har både start- og slutdato
        if isinstance(valgt_dato, (list, tuple)) and len(valgt_dato) == 2:
            query &= (df_log['Dato'] >= valgt_dato[0]) & (df_log['Dato'] <= valgt_dato[1])

        df_filtered = df_log[query].sort_values("Dato", ascending=False)

        # --- VISNING ---
        st.markdown("---") 
        if not df_filtered.empty:
            # Brug st.dataframe i stedet for st.table, hvis loggen er lang (giver scrollbar)
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.info("Ingen log-poster fundet med de valgte filtre.")
            
    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")
