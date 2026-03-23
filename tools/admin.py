import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime

def vis_log():
    st.caption("### Log")
    
    try:
        # 1. Hent data fra GitHub
        token = st.secrets["GITHUB_TOKEN"]
        repo = "Kamudinho/HIF-data"
        path = "data/action_log.csv"
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            content = base64.b64decode(r.json()['content']).decode('utf-8')
            df = pd.read_csv(StringIO(content))
            
            # Konverter Dato til datetime format så sortering og dato-filter virker
            df['Dato'] = pd.to_datetime(df['Dato'], errors='coerce')
            
            # --- FILTRERING ---
            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    brugere = sorted(df["Bruger"].dropna().unique().tolist())
                    valgte_brugere = st.multiselect("Filtrer på Bruger", options=brugere)
                
                with c2:
                    handlinger = sorted(df["Handling"].dropna().unique().tolist())
                    valgte_handlinger = st.multiselect("Filtrer på Handling", options=handlinger)
                
                with c3:
                    # Dato filter
                    if not df.empty and df['Dato'].notnull().any():
                        min_d = df["Dato"].min().date()
                        max_d = df["Dato"].max().date()
                        dato_valg = st.date_input("Dato interval", value=(min_d, max_d))
                    else:
                        dato_valg = None

                search = st.text_input("Søg i 'Mål' (Kontekst)")

            # --- ANVEND LOGIK ---
            df_final = df.copy()
            
            if valgte_brugere:
                df_final = df_final[df_final["Bruger"].isin(valgte_brugere)]
            
            if valgte_handlinger:
                df_final = df_final[df_final["Handling"].isin(valgte_handlinger)]
                
            if dato_valg and isinstance(dato_valg, tuple) and len(dato_valg) == 2:
                df_final = df_final[(df_final["Dato"].dt.date >= dato_valg[0]) & (df_final["Dato"].dt.date <= dato_valg[1])]
                
            if search:
                df_final = df_final[df_final["Mål"].str.contains(search, case=False, na=False)]

            # --- VISNING ---
            st.write(f"Viser {len(df_final)} hændelser")
            
            st.dataframe(
                df_final.sort_values("Dato", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Dato": st.column_config.DatetimeColumn("Tidspunkt", format="DD/MM/YYYY HH:mm"),
                    "Bruger": "Bruger",
                    "Handling": "Handling",
                    "Mål": "Kontekst / Detaljer"
                }
            )

        else:
            st.error(f"Kunne ikke hente log fra GitHub (Fejl {r.status_code})")

    except Exception as e:
        st.error(f"Der opstod en fejl: {e}")
