import streamlit as st
import pandas as pd
import uuid

def vis_side():
    """Viser brugeroversigt og profilrettigheder."""
    if st.session_state.get("role") != "admin":
        st.error("Adgang nægtet.")
        return

    st.write("### Brugerstyring")
    from data.users import get_users
    users = get_users()
    
    user_data = []
    for u, info in users.items():
        user_data.append({"Brugernavn": u, "Rolle": info["role"]})
    
    st.table(pd.DataFrame(user_data))
    st.info("Rettigheder styres pt. via data/users.py")

def vis_log():
    """Viser systemets aktivitetslog fra GitHub."""
    if st.session_state.get("role") != "admin":
        st.error("Adgang nægtet.")
        return

    st.write("### System Log")
    
    try:
        # Cache-busting URL for at sikre vi ser de nyeste handlinger
        url = f"https://raw.githubusercontent.com/Kamudinho/HIF-data/main/data/action_log.csv?nocache={uuid.uuid4()}"
        df_log = pd.read_csv(url)
        st.dataframe(
            df_log.sort_values("Dato", ascending=False), 
            use_container_width=True, 
            hide_index=True
        )
    except Exception as e:
        st.warning("Kunne ikke hente log-filen. Den oprettes automatisk ved næste handling.")
