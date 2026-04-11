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
# Vi henter token direkte fra Streamlit Secrets
TOKEN = st.secrets["GITHUB_TOKEN"]

def get_github_headers():
    return {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Cache-Control": "no-cache"
    }

def save_action_log(bruger, handling, mal):
    """
    Brug denne funktion i resten af appen til at logge handlinger.
    Den henter automatisk SHA, så den aldrig fejler pga. manuelle rettelser.
    """
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}"
    headers = get_github_headers()

    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            file_data = r.json()
            sha = file_data['sha']
            content = base64.b64decode(file_data['content']).decode('utf-8')
            
            # Formatering af ny linje
            clean_mal = str(mal).replace(",", ";")
            tidsstempel = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ny_linje = f"{tidsstempel},{bruger},{handling},{clean_mal}\n"
            
            # Fix hvis filen ikke slutter med linjeskift
            if content and not content.endswith('\n'):
                content += '\n'
            
            opdateret_indhold = content + ny_linje
            
            payload = {
                "message": f"Log update: {bruger}",
                "content": base64.b64encode(opdateret_indhold.encode('utf-8')).decode('utf-8'),
                "sha": sha
            }
            
            requests.put(url, headers=headers, json=payload)
            return True
    except:
        return False

def vis_log():
    st.title("🛡️ Admin Panel")
    st.markdown("### System Action Log")
    
    # Cache-busting sikrer, at vi ser de nyeste ændringer med det samme
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}?t={int(time.time())}"
    headers = get_github_headers()

    try:
        r = requests.get(url, headers=headers)
        
        if r.status_code == 200:
            raw_content = base64.b64decode(r.json()['content']).decode('utf-8')
            
            # 'on_bad_lines' springer den ødelagte linje fra d. 25/3 over
            df = pd.read_csv(StringIO(raw_content), on_bad_lines='skip')
            
            # Konvertering og oprydning
            df['Dato'] = pd.to_datetime(df['Dato'], errors='coerce')
            df = df.dropna(subset=['Dato'])
            
            # --- FILTER SEKTION ---
            with st.expander("Filter indstillinger", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    brugere = sorted(df["Bruger"].unique().tolist())
                    v_bruger = st.multiselect("Filtrer Bruger", brugere)
                with c2:
                    handlinger = sorted(df["Handling"].unique().tolist())
                    v_handling = st.multiselect("Filtrer Handling", handlinger)
                
                søg = st.text_input("Søg i detaljer/mål")

            # --- ANVEND FILTRE ---
            mask = pd.Series([True] * len(df))
            if v_bruger:
                mask &= df["Bruger"].isin(v_bruger)
            if v_handling:
                mask &= df["Handling"].isin(v_handling)
            if søg:
                mask &= df["Mål"].astype(str).str.contains(søg, case=False, na=False)
            
            df_vis = df[mask].sort_values("Dato", ascending=False)

            # --- VISNING ---
            st.dataframe(
                df_vis,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Dato": st.column_config.DatetimeColumn("Tidspunkt", format="DD/MM/YYYY HH:mm:ss"),
                    "Bruger": "Bruger",
                    "Handling": "Handling",
                    "Mål": "Kontekst/Detaljer"
                }
            )
            
            if st.button("Opdater data"):
                st.rerun()
        else:
            st.warning(f"Kunne ikke hente loggen. Statuskode: {r.status_code}")

    except Exception as e:
        st.error(f"Der skete en fejl: {e}")

if __name__ == "__main__":
    vis_log()
