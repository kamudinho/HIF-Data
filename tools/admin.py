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
    """Viser systemets aktivitetslog med filtre og fuld tabelvisning."""
    aktuel_rolle = str(st.session_state.get("role", "")).lower()
    
    if aktuel_rolle != "admin":
        st.error("Adgang nægtet.")
        return

    st.write("### System Log")
    
    try:
        import uuid
        url = f"https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/action_log.csv?nocache={uuid.uuid4()}"
        df_log = pd.read_csv(url)
        
        # Sørg for at datoen er i rigtigt format
        df_log['Dato'] = pd.to_datetime(df_log['Dato']).dt.date
        
        # --- FILTRE ---
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filter på Bruger
            brugere = ["Alle"] + sorted(df_log['Bruger'].unique().tolist())
            valgt_bruger = st.selectbox("Filtrer på Bruger", brugere)
            
        with col2:
            # Filter på Handling/Mål (kolonnen hedder typisk 'Handling' eller 'Action')
            # Jeg antager her kolonnen hedder 'Handling' - ret evt. til 'Mål' hvis det er navnet
            handling_col = 'Handling' if 'Handling' in df_log.columns else df_log.columns[2]
            handlinger = ["Alle"] + sorted(df_log[handling_col].unique().tolist())
            valgt_handling = st.selectbox(f"Filtrer på {handling_col}", handlinger)
            
        with col3:
            # Filter på Dato
            min_dato = df_log['Dato'].min()
            max_dato = df_log['Dato'].max()
            valgt_dato = st.date_input("Vælg datointerval", [min_dato, max_dato])

        # --- ANVEND FILTRE ---
        mask = pd.Series([True] * len(df_log))
        
        if valgt_bruger != "Alle":
            mask &= (df_log['Bruger'] == valgt_bruger)
        
        if valgt_handling != "Alle":
            mask &= (df_log[handling_col] == valgt_handling)
            
        if len(valgt_dato) == 2:
            mask &= (df_log['Dato'] >= valgt_dato[0]) & (df_log['Dato'] <= valgt_dato[1])

        df_filtered = df_log[mask].sort_values("Dato", ascending=False)

        # --- VISNING ---
        # st.table fjerner scroll-boksen og viser ALLE rækker direkte på siden
        if not df_filtered.empty:
            st.table(df_filtered)
        else:
            st.info("Ingen log-poster matcher de valgte filtre.")
            
    except Exception as e:
        st.warning(f"Kunne ikke hente log-filen: {e}")
