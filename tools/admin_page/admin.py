import streamlit as st
import pandas as pd
import requests
import base64
import csv
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

def _hent_fil():
    """Henter rå filindhold + sha fra GitHub. Kaster exception ved fejl."""
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}?t={int(time.time())}"
    r = requests.get(url, headers=get_github_headers())
    r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data['content']).decode('utf-8')
    return content, data['sha']

def _byg_csv_linje(tidsstempel, bruger, handling, mal):
    """
    Bygger en korrekt escaped CSV-linje ved hjælp af csv-modulet.
    Dette er den vigtige rettelse: hvis handling/mål indeholder komma,
    anførselstegn eller linjeskift, bliver det nu escaped korrekt i
    stedet for at ødelægge resten af filens struktur.
    """
    # Fjern evt. interne linjeskift, så et enkelt logopslag aldrig
    # kan brede sig over flere CSV-rækker
    ren = lambda x: str(x).replace("\n", " ").replace("\r", " ").strip()

    buffer = StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([tidsstempel, ren(bruger), ren(handling), ren(mal)])
    return buffer.getvalue()  # csv.writer tilføjer selv \r\n eller \n

def save_action_log(bruger, handling, mal, _forsoeg=0):
    """
    Logger en handling til CSV-filen på GitHub.
    Returnerer True ved succes, False ved fejl (fejl vises også via st.error,
    så fejl ikke længere forsvinder stille).
    Prøver automatisk igen én gang ved 409-konflikt (samtidig skrivning).
    """
    url = f"https://api.github.com/repos/{REPO}/contents/{PATH}"
    headers = get_github_headers()

    try:
        content, sha = _hent_fil()

        tidsstempel = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ny_linje = _byg_csv_linje(tidsstempel, bruger, handling, mal)

        if content and not content.endswith('\n'):
            content += '\n'

        opdateret_indhold = content + ny_linje

        payload = {
            "message": f"Log update: {bruger}",
            "content": base64.b64encode(opdateret_indhold.encode('utf-8')).decode('utf-8'),
            "sha": sha
        }

        put_r = requests.put(url, headers=headers, json=payload)

        if put_r.status_code in (200, 201):
            return True

        if put_r.status_code == 409 and _forsoeg < 1:
            # SHA'en var forældet, fordi en anden skrev til filen først.
            # Hent frisk sha og prøv igen én gang.
            return save_action_log(bruger, handling, mal, _forsoeg=_forsoeg + 1)

        st.error(f"Kunne ikke gemme log-handling. GitHub svarede: {put_r.status_code} – {put_r.text}")
        return False

    except Exception as e:
        st.error(f"Fejl ved skrivning til log: {e}")
        return False


def vis_log():
    st.markdown("### System Action Log")

    try:
        content, _ = _hent_fil()

        # 'warn' i stedet for 'skip' så du kan se i konsollen hvis der
        # stadig er en ødelagt række et sted
        df = pd.read_csv(StringIO(content), on_bad_lines='warn', engine="python")

        df['Dato'] = pd.to_datetime(df['Dato'], errors='coerce')
        antal_ugyldige = df['Dato'].isna().sum()
        if antal_ugyldige:
            st.warning(
                f"⚠️ {antal_ugyldige} række(r) i loggen kunne ikke tolkes korrekt "
                f"og vises ikke. Det tyder på en beskadiget linje i CSV-filen."
            )
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

    except requests.exceptions.HTTPError as e:
        st.warning(f"Kunne ikke hente loggen fra GitHub: {e}")
    except Exception as e:
        st.error(f"Der skete en fejl: {e}")


if __name__ == "__main__":
    vis_log()
