import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO

def vis_log():
    st.title("📊 System Action Log")
    
    try:
        # 1. Hent data fra GitHub
        token = st.secrets["GITHUB_TOKEN"]
        repo = "Kamudinho/HIF-data"
        path = "data/action_log.csv"
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {token}"}

        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            content = base64.b64decode(r.json()['content']).decode('utf-8')
            df = pd.read_csv(StringIO(content))
            df['Dato'] = pd.to_datetime(df['Dato'])
            
            # --- FILTRE ØVERST ---
            col1, col2, col3 = st.columns(3)
            with col1:
                bruger_filter = st.multiselect("Filtrer på Bruger", options=df["Bruger"].unique())
            with col2:
                handling_filter = st.multiselect("Filtrer på Handling", options=df["Handling"].unique())
            with col3:
                search = st.text_input("Søg i Mål (f.eks. spillernavn)")

            # Anvend filtre
            df_filtered = df.copy()
            if bruger_filter:
                df_filtered = df_filtered[df_filtered["Bruger"].isin(bruger_filter)]
            if handling_filter:
                df_filtered = df_filtered[df_filtered["Handling"].isin(handling_filter)]
            if search:
                df_filtered = df_filtered[df_filtered["Mål"].str.contains(search, case=False, na=False)]

            # --- VISNING ---
            st.markdown("---")
            st.dataframe(
                df_filtered.sort_values("Dato", ascending=False), 
                use_container_width=True,
                hide_index=True
            )
            
            # Lille statistik-tæller i bunden
            st.caption(f"Viser {len(df_filtered)} hændelser ud af i alt {len(df)} logget.")
            
        elif r.status_code == 404:
            st.info("Log-filen er tom eller ikke oprettet endnu.")
        else:
            st.error(f"GitHub fejlkode: {r.status_code}")

    except Exception as e:
        st.error(f"Kunne ikke indlæse log-data: {e}")
