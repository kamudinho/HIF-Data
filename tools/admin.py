import streamlit as st
import pandas as pd
import uuid

def vis_side():
    """Viser brugeroversigt og profilrettigheder."""
    # Hent rollen og lav den til små bogstaver for at undgå 'Adgang nægtet' pga. stort bogstav
    aktuel_rolle = str(st.session_state.get("role", "")).lower()

    if aktuel_rolle != "admin":
        st.error(f"Adgang nægtet. Din nuværende rolle er '{aktuel_rolle}', men siden kræver 'admin'.")
        # Tip: Hvis rollen er tom herover, ligger fejlen i dit login-script
        return

    st.write("### Brugerstyring")
    from data.users import get_users
    users = get_users()
    
    user_data = []
    for u, info in users.items():
        # 'Brugernavn' her er bare en overskrift i tabellen - den må gerne have stort B
        user_data.append({"Brugernavn": u, "Rolle": info["role"]})
    
    st.table(pd.DataFrame(user_data))
    st.info("Rettigheder styres pt. via data/users.py")

def vis_log():
    """Viser systemets aktivitetslog med filtre placeret over tabellen."""
    aktuel_rolle = str(st.session_state.get("role", "")).lower()
    
    if aktuel_rolle != "admin":
        st.error("Adgang nægtet.")
        return

    st.write("### System Log")
    
    try:
        import uuid
        # Cache-busting for at hente nyeste data fra GitHub
        url = f"https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/action_log.csv?nocache={uuid.uuid4()}"
        df_log = pd.read_csv(url)
        
        # Konverter datoer så de kan filtreres korrekt
        df_log['Dato'] = pd.to_datetime(df_log['Dato']).dt.date
        
        # --- FILTRE ØVERST ---
        st.markdown("#### Filtre")
        f1, f2, f3, f4 = st.columns(4)
        
        with f1:
            # Filter: Bruger
            brugere = ["Alle"] + sorted(df_log['Bruger'].unique().astype(str).tolist())
            valgt_bruger = st.selectbox("Bruger", brugere)
            
        with f2:
            # Filter: Handling
            handlinger = ["Alle"] + sorted(df_log['Handling'].unique().astype(str).tolist())
            valgt_handling = st.selectbox("Handling", handlinger)
            
        with f3:
            # Filter: Mål (Jeg antager kolonnen hedder 'Mål')
            maal_list = ["Alle"] + sorted(df_log['Mål'].unique().astype(str).tolist())
            valgt_maal = st.selectbox("Mål", maal_list)
            
        with f4:
            # Filter: Dato-interval
            min_d = df_log['Dato'].min()
            max_d = df_log['Dato'].max()
            valgt_dato = st.date_input("Dato-interval", [min_d, max_d])

        # --- ANVEND FILTRERING ---
        query = pd.Series([True] * len(df_log))
        
        if valgt_bruger != "Alle":
            query &= (df_log['Bruger'] == valgt_bruger)
        
        if valgt_handling != "Alle":
            query &= (df_log['Handling'] == valgt_handling)

        if valgt_maal != "Alle":
            query &= (df_log['Mål'] == valgt_maal)
            
        if len(valgt_dato) == 2:
            query &= (df_log['Dato'] >= valgt_dato[0]) & (df_log['Dato'] <= valgt_dato[1])

        df_filtered = df_log[query].sort_values("Dato", ascending=False)

        # --- VISNING ---
        st.markdown("---") # En lille adskiller linje
        if not df_filtered.empty:
            # st.table viser alt uden scroll-bar
            st.table(df_filtered)
        else:
            st.info("Ingen log-poster fundet med de valgte filtre.")
            
    except Exception as e:
        st.warning(f"Kunne ikke hente log-filen: {e}. Tjek om kolonnenavnene 'Bruger', 'Handling' og 'Mål' er korrekte i din CSV.")
