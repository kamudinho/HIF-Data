import streamlit as st
import pandas as pd
import requests
import base64
import csv
import threading
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
    r = requests.get(url, headers=get_github_headers(), timeout=5)
    r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data['content']).decode('utf-8')
    return content, data['sha']

def _byg_csv_linje(tidsstempel, bruger, handling, mal):
    """
    Bygger en korrekt escaped CSV-linje ved hjælp af csv-modulet, så komma/
    anførselstegn/linjeskift i felterne ikke ødelægger filens struktur.
    """
    ren = lambda x: str(x).replace("\n", " ").replace("\r", " ").strip()

    buffer = StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([tidsstempel, ren(bruger), ren(handling), ren(mal)])
    return buffer.getvalue()

def _save_action_log_sync(bruger, handling, mal, _forsoeg=0):
    """
    Selve skrive-logikken - kører i en baggrundstråd (se save_action_log
    nedenfor), og kalder derfor ALDRIG st.* (Streamlit's UI-kald er ikke
    trådsikre uden for hovedtråden). Fejl skrives til konsol/logs i stedet.

    Retry-strategi:
    - 409 (SHA-konflikt, fx to samtidige skrivninger): prøv igen med kort
      eksponentiel backoff, op til 3 forsøg - det er et forbigående problem.
    - 429 (rate limit fra GitHub): prøver IKKE igen. At blive ved med at
      banke på når GitHub beder om ro, forværrer kun rate-limiteringen.
      Fejlen logges og opgives med det samme.
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

        put_r = requests.put(url, headers=headers, json=payload, timeout=5)

        if put_r.status_code in (200, 201):
            return True

        if put_r.status_code == 409 and _forsoeg < 3:
            time.sleep(0.2 * (2 ** _forsoeg))
            return _save_action_log_sync(bruger, handling, mal, _forsoeg=_forsoeg + 1)

        if put_r.status_code == 429:
            print(f"[action_log] Rate limited af GitHub (429) - dropper dette log-forsøg for {bruger}.")
            return False

        print(f"[action_log] Kunne ikke gemme log-handling. GitHub svarede: {put_r.status_code} – {put_r.text}")
        return False

    except Exception as e:
        print(f"[action_log] Fejl ved skrivning til log: {e}")
        return False


def save_action_log(bruger, handling, mal):
    """
    Logger en handling til CSV-filen på GitHub - ASYNKRONT (fire-and-forget).

    Selve netværkskaldet køres i en baggrundstråd, så et langsomt eller
    rate-limitet GitHub-kald aldrig blokerer sideindlæsningen for brugeren.
    Funktionen returnerer med det samme og venter ikke på resultatet.

    Fejl vises ikke i UI'en (det ville kræve at vente på tråden) - de
    printes til konsol/Streamlit-logs i stedet. Det er en bevidst afvejning:
    logning er "best effort" og må aldrig gå ud over app-oplevelsen.
    """
    thread = threading.Thread(
        target=_save_action_log_sync,
        args=(bruger, handling, mal),
        daemon=True
    )
    thread.start()


def vis_log():
    st.markdown("### System Action Log")

    try:
        content, _ = _hent_fil()

        df = pd.read_csv(StringIO(content), on_bad_lines='warn', engine="python")

        df['Dato'] = pd.to_datetime(df['Dato'], errors='coerce')
        antal_ugyldige = df['Dato'].isna().sum()
        if antal_ugyldige:
            st.warning(
                f"⚠️ {antal_ugyldige} række(r) i loggen kunne ikke tolkes korrekt "
                f"og vises ikke."
            )
        df = df.dropna(subset=['Dato'])

        with st.expander("Filter indstillinger", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                brugere = sorted(df["Bruger"].unique().tolist())
                v_bruger = st.multiselect("Filtrer Bruger", brugere)
            with c2:
                handlinger = sorted(df["Handling"].unique().tolist())
                v_handling = st.multiselect("Filtrer Handling", handlinger)

            søg = st.text_input("Søg i detaljer/mål")

        mask = pd.Series([True] * len(df))
        if v_bruger:
            mask &= df["Bruger"].isin(v_bruger)
        if v_handling:
            mask &= df["Handling"].isin(v_handling)
        if søg:
            mask &= df["Mål"].astype(str).str.contains(søg, case=False, na=False)

        df_vis = df[mask].sort_values("Dato", ascending=False)

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
