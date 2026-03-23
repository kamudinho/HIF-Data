import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime

def vis_log():
    st.caption("System Log")
    
    try:
        # 1. Hent data fra GitHub
        token = st.secrets["GITHUB_TOKEN"]
        repo = "Kamudinho/HIF-data"
        path = "data/action_log.csv"
        url = f"https://api.github.com/repos/{repo}/contents/{path}"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            # Dekod indholdet
            content = base64.b64decode(r.json()['content']).decode('utf-8')
            df = pd.read_csv(StringIO(content))
            
            # Konverter Dato til rigtigt dato-format så vi kan sortere korrekt
            df['Dato'] = pd.to_datetime(df['Dato'], errors='coerce')
            
            # --- FILTER SEKTION ---
            with st.expander("🔍 Filtrer Log-data", expanded=True):
                c1, c2, c3 = st.columns(3)
                
                with c1:
                    # Bruger-filter (viser alle unikke brugere i loggen)
                    alle_brugere = sorted(df["Bruger"].dropna().unique())
                    valgte_brugere = st.multiselect("Vælg Bruger(e)", options=alle_brugere)
                
                with c2:
                    # Handlings-filter
                    alle_handlinger = sorted(df["Handling"].dropna().unique())
                    valgte_handlinger = st.multiselect("Vælg Handling(er)", options=alle_handlinger)
                
                with c3:
                    # Dato-filter
                    min_dato = df["Dato"].min().date() if not df.empty else datetime.now().date()
                    max_dato = df["Dato"].max().date() if not df.empty else datetime.now().date()
                    dato_range = st.date_input("Vælg Dato-interval", value=(min_dato, max_dato))

                search_term = st.text_input("Søg i 'Mål' (f.eks. modstander eller spillernavn)")

            # --- ANVEND FILTRE ---
            mask = pd.Series([True] * len(df))
            
            if valgte_brugere:
                mask &= df["Bruger"].isin(valgte_brugere)
            
            if valgte_handlinger:
                mask &= df["Handling"].isin(valgte_handlinger)
                
            if isinstance(dato_range, tuple) and len(dato_range) == 2:
                mask &= (df["Dato"].dt.date >= dato_range[0]) & (df["Dato"].dt.date <= dato_range[1])
                
            if search_term:
                mask &= df["Mål"].str.contains(search_term, case=False, na=False)

            df_display = df[mask].sort_values("Dato", ascending=False)

            # --- VISNING ---
            st.markdown(f"**Viser {len(df_display)} ud af {len(df)} hændelser**")
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Dato": st.column_config.DatetimeColumn("Tidspunkt", format="DD/MM/YYYY HH:mm"),
                    "Bruger": st.column_config.TextColumn("Bruger"),
                    "Handling": st.column_config.TextColumn("Handling"),
                    "Mål": st.column_config.TextColumn("Kontekst/Mål")
                }
            )
            
            # Download-mulighed
            csv_data = df_display.to_csv(index=False).encode('utf-8')
            st.download_button("Export til CSV", data=csv_data, file_name="hif_action_log.csv", mime="text/csv")

        elif r.status_code == 404:
            st.info("Log-filen blev ikke fundet på GitHub. Den oprettes automatisk ved næste log-hændelse.")
        else:
            st.error(f"Kunne ikke hente loggen. GitHub svarede med statuskode: {r.status_code}")

    except Exception as e:
        st.error(f"Der opstod en fejl i Admin-modulet: {e}")
