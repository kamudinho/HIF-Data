import streamlit as st
import pandas as pd
import uuid

def vis_log():
    """Viser systemets aktivitetslog med filtre."""
    # DEBUG: Så vi kan se om forbindelsen virker
    st.sidebar.success("✅ profil.py er indlæst")
    
    aktuel_rolle = str(st.session_state.get("role", "")).lower().strip()
    
    if aktuel_rolle != "admin":
        st.error(f"Adgang nægtet. Din rolle er '{aktuel_rolle}', men 'admin' kræves.")
        return

    st.write("### System Log")
    
    try:
        # Cache-busting URL
        url = f"https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/action_log.csv?nocache={uuid.uuid4()}"
        df_log = pd.read_csv(url)
        
        # Rens data
        df_log.columns = [c.strip() for c in df_log.columns]
        df_log['Dato'] = pd.to_datetime(df_log['Dato']).dt.date
        
        # Filtre
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            valgt_bruger = st.selectbox("Bruger", ["Alle"] + sorted(df_log['Bruger'].unique().tolist()))
        with f2:
            valgt_handling = st.selectbox("Handling", ["Alle"] + sorted(df_log['Handling'].unique().tolist()))
        with f3:
            valgt_maal = st.selectbox("Mål", ["Alle"] + sorted(df_log['Mål'].unique().tolist()))
        with f4:
            valgt_dato = st.date_input("Dato-interval", [df_log['Dato'].min(), df_log['Dato'].max()])

        # Filtrering
        query = pd.Series([True] * len(df_log))
        if valgt_bruger != "Alle": query &= (df_log['Bruger'] == valgt_bruger)
        if valgt_handling != "Alle": query &= (df_log['Handling'] == valgt_handling)
        if valgt_maal != "Alle": query &= (df_log['Mål'] == valgt_maal)
        if isinstance(valgt_dato, (list, tuple)) and len(valgt_dato) == 2:
            query &= (df_log['Dato'] >= valgt_dato[0]) & (df_log['Dato'] <= valgt_dato[1])

        df_filtered = df_log[query].sort_values("Dato", ascending=False)

        st.markdown("---")
        if not df_filtered.empty:
            st.dataframe(df_filtered, use_container_width=True)
        else:
            st.info("Ingen log-poster fundet.")
            
    except Exception as e:
        st.error(f"Fejl ved indlæsning af log: {e}")
