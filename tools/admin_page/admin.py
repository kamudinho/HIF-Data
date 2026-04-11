import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
from datetime import datetime
import time

# --- KONFIGURATION (Hent fra st.secrets) ---
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
    Denne funktion skal kaldes andre steder i din app for at gemme en hændelse.
    Den løser '25/3-problemet' ved altid at hente den nyeste SHA-nøgle før skrivning.
    """
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}"
    headers = get_github_headers()

    try:
        # 1. Hent den nuværende fil for at få fat i den korrekte 'sha'
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            file_data = r.json()
            sha = file_data['sha']
            content = base64.b64decode(file_data['content']).decode('utf-8')
            
            # 2. Forbered ny linje (Sikr at mal ikke indeholder kommaer der ødelægger CSV)
            clean_mal = str(mal).replace(",", ";")
            tidsstempel = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ny_linje = f"{tidsstempel},{bruger},{handling},{clean_mal}\n"
            
            # Sørg for at filen slutter med newline hvis den er tom
            if content and not content.endswith('\n'):
                content += '\n'
            
            opdateret_indhold = content + ny_linje
            
            # 3. Push tilbage til GitHub
            payload = {
                "message": f"Log: {handling} af {bruger}",
                "content": base64.b64encode(opdateret_indhold.encode('utf-8')).decode('utf-8'),
                "sha": sha
            }
            
            put_r = requests.put(url, headers=headers, json=payload)
            return put_r.status_code == 200
        return False
    except:
        return False

def vis_log():
    st.markdown("### System Action Log")
    
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}?t={int(time.time())}"
    headers = get_github_headers()

    try:
        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            content = base64.b64decode(r.json()['content']).decode('utf-8')
            df = pd.read_csv(StringIO(content))
            
            # Robust dato-konvertering (vigtigt for filteret)
            df['Dato'] = pd.to_datetime(df['Dato'], dayfirst=False, errors='coerce')
            
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
                    # Dato filter - tjek for gyldige datoer
                    valid_df = df.dropna(subset=['Dato'])
                    if not valid_df.empty:
                        min_d = valid_df["Dato"].min().date()
                        max_d = valid_df["Dato"].max().date()
                        # date_input returnerer en tuple (start, slut)
                        dato_valg = st.date_input("Dato interval", value=(min_d, max_d))
                    else:
                        dato_valg = None

                search = st.text_input("Søg i kontekst (Mål)", placeholder="Søg efter spillernavne, hold osv...")

            # --- ANVEND LOGIK ---
            df_final = df.copy()
            
            if valgte_brugere:
                df_final = df_final[df_final["Bruger"].isin(valgte_brugere)]
            
            if valgte_handlinger:
                df_final = df_final[df_final["Handling"].isin(valgte_handlinger)]
                
            if dato_valg and isinstance(dato_valg, (list, tuple)) and len(dato_valg) == 2:
                df_final = df_final[
                    (df_final["Dato"].dt.date >= dato_valg[0]) & 
                    (df_final["Dato"].dt.date <= dato_valg[1])
                ]
                
            if search:
                # Vi tjekker kolonnen 'Mål' som i din CSV svarer til kontekst
                df_final = df_final[df_final["Mål"].astype(str).str.contains(search, case=False, na=False)]

            # --- VISNING ---
            st.write(f"Viser **{len(df_final)}** hændelser")
            
            st.dataframe(
                df_final.sort_values("Dato", ascending=False),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Dato": st.column_config.DatetimeColumn("Tidspunkt", format="DD/MM/YYYY HH:mm"),
                    "Bruger": st.column_config.TextColumn("Bruger"),
                    "Handling": st.column_config.TextColumn("Handling"),
                    "Mål": st.column_config.TextColumn("Kontekst / Detaljer")
                }
            )

            # En lille 'Refresh' knap til manuel genindlæsning
            if st.button("Opdater log"):
                st.rerun()

        elif r.status_code == 401:
            st.error("GitHub fejl: Din TOKEN er udløbet eller ugyldig (401).")
        else:
            st.error(f"Kunne ikke hente log fra GitHub (Fejl {r.status_code})")

    except Exception as e:
        st.error(f"Der opstod en uventet fejl: {e}")

# Hvis du vil teste funktionen direkte
if __name__ == "__main__":
    vis_log()
