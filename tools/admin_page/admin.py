import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime
import time

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
PATH = "data/action_log.csv"
TOKEN = st.secrets["GITHUB_TOKEN"]

def get_github_headers():
    return {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Cache-Control": "no-cache"
    }

def save_action_log(bruger, handling, mal):
    """
    Gemmer en hændelse i GitHub CSV-filen.
    Henter altid nyeste SHA for at undgå konflikter.
    """
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}"
    headers = get_github_headers()

    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            file_data = r.json()
            sha = file_data['sha']
            content = base64.b64decode(file_data['content']).decode('utf-8')
            
            clean_mal = str(mal).replace(",", ";")
            tidsstempel = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ny_linje = f"{tidsstempel},{bruger},{handling},{clean_mal}\n"
            
            if content and not content.endswith('\n'):
                content += '\n'
            
            opdateret_indhold = content + ny_linje
            
            payload = {
                "message": f"Log update: {bruger}",
                "content": base64.b64encode(opdateret_indhold.encode('utf-8')).decode('utf-8'),
                "sha": sha
            }
            
            put_r = requests.put(url, headers=headers, json=payload)
            return put_r.status_code == 200
        return False
    except:
        return False

def vis_log():
    st.markdown("### 📋 System Action Log")
    
    # Cache-busting t=timestamp sikrer at vi henter det nyeste data hver gang
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}?t={int(time.time())}"
    headers = get_github_headers()

    try:
        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            raw_content = base64.b64decode(r.json()['content']).decode('utf-8')
            
            # on_bad_lines='skip' sikrer at den klippede linje fra 25/3 ikke ødelægger appen
            df = pd.read_csv(StringIO(raw_content), on_bad_lines='skip')
            
            # Konverter datoer og ryd op
            df['Dato'] = pd.to_datetime(df['Dato'], errors='coerce')
            df = df.dropna(subset=['Dato']) # Fjern linjer der er korrupte
            
            # --- FILTRERING ---
            with st.expander("Filter og Søgning", expanded=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    brugere = sorted(df["Bruger"].unique().tolist())
                    valgte_brugere = st.multiselect("Bruger", options=brugere)
                with c2:
                    handlinger = sorted(df["Handling"].unique().tolist())
                    valgte_handlinger = st.multiselect("Handling", options=handlinger)
                with c3:
                    min_d = df["Dato"].min().date()
                    max_d = df["Dato"].max().date()
                    dato_valg = st.date_input("Dato interval", value=(min_d, max_d))

                search = st.text_input("Søg i detaljer", placeholder="Søg efter fane, spiller eller hold...")

            # --- LOGIK ---
            df_final = df.copy()
            if valgte_brugere:
                df_final = df_final[df_final["Bruger"].isin(valgte_brugere)]
            if valgte_handlinger:
                df_final = df_final[df_final["Handling"].isin(valgte_handlinger)]
            if isinstance(dato_valg, (list, tuple)) and len(dato_valg) == 2:
                df_final = df_final[(df_final["Dato"].dt.date >= dato_valg[0]) & (df_final["Dato"].dt.date <= dato_valg[1])]
            if search:
                df_final = df_final[df_final["Mål"].astype(str).str.contains(search, case=False, na=False)]

            # --- VISNING ---
            st.dataframe(
                df_final.sort_values("Dato", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Dato": st.column_config.DatetimeColumn("Tidspunkt", format="DD/MM/YYYY HH:mm"),
                    "Mål": st.column_config.TextColumn("Detaljer")
                }
            )
            
            if st.button("🔄 Opdater nu"):
                st.rerun()

        elif r.status_code == 401:
            st.error("Fejl: GitHub Token er ugyldig.")
        else:
            st.info("Loggen er tom eller kunne ikke hentes.")

    except Exception as e:
        st.error(f"Fejl ved indlæsning: {e}")

if __name__ == "__main__":
    vis_log()
