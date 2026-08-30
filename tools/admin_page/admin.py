import streamlit as st
import requests
import base64
import time
from datetime import datetime

REPO = "Kamudinho/HIF-data"
PATH = "data/action_log.csv"

st.title("🔧 GitHub Log – Diagnose")
st.caption("Tester forbindelsen trin for trin, så vi kan se præcis hvor det knækker.")

TOKEN = st.secrets.get("GITHUB_TOKEN", None)

if not TOKEN:
    st.error("Der er slet ikke sat en GITHUB_TOKEN i st.secrets. Tjek Streamlit Cloud > Settings > Secrets.")
    st.stop()

st.success(f"Token fundet i secrets (længde: {len(TOKEN)} tegn, starter med '{TOKEN[:7]}...').")

headers = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Cache-Control": "no-cache"
}

# --- TRIN 1: Er tokenet overhovedet gyldigt? ---
st.markdown("### Trin 1: Er token gyldigt?")
r1 = requests.get("https://api.github.com/user", headers=headers)
if r1.status_code == 200:
    bruger_info = r1.json()
    st.success(f"✅ Token er gyldigt. Autentificeret som: **{bruger_info.get('login')}**")
else:
    st.error(f"❌ Token er IKKE gyldigt. Status: {r1.status_code}")
    st.code(r1.text)
    st.info("Løsning: Opret et nyt Personal Access Token på GitHub og opdater det i Streamlit Secrets.")
    st.stop()

# --- TRIN 2: Har tokenet adgang til repoet? ---
st.markdown("### Trin 2: Har token adgang til repoet?")
r2 = requests.get(f"https://api.github.com/repos/{REPO}", headers=headers)
if r2.status_code == 200:
    repo_info = r2.json()
    st.success(f"✅ Repo fundet: **{repo_info.get('full_name')}** (privat: {repo_info.get('private')})")
    st.write(f"Din bruger har permissions: {repo_info.get('permissions')}")
else:
    st.error(f"❌ Kan ikke tilgå repoet '{REPO}'. Status: {r2.status_code}")
    st.code(r2.text)
    if r2.status_code == 404:
        st.info("Enten er repo-navnet forkert/omdøbt, eller også har tokenet ikke adgang til det (fx hvis repoet er blevet privat, eller det er et fine-grained token uden adgang til dette repo).")
    st.stop()

# --- TRIN 3: Kan vi finde selve filen? ---
st.markdown("### Trin 3: Kan filen findes?")
url = f"https://api.github.com/repos/{REPO}/contents/{PATH}?t={int(time.time())}"
r3 = requests.get(url, headers=headers)
if r3.status_code == 200:
    file_data = r3.json()
    sha = file_data['sha']
    content = base64.b64decode(file_data['content']).decode('utf-8')
    antal_linjer = content.count('\n')
    st.success(f"✅ Filen findes. SHA: {sha[:10]}... Antal linjer (ca.): {antal_linjer}")
    sidste_linjer = "\n".join(content.strip().split("\n")[-3:])
    st.code(sidste_linjer, language="text")
else:
    st.error(f"❌ Kan ikke hente filen '{PATH}'. Status: {r3.status_code}")
    st.code(r3.text)
    st.stop()

# --- TRIN 4: Kan vi rent faktisk SKRIVE til filen? ---
st.markdown("### Trin 4: Test-skrivning")
st.write("Dette forsøger at skrive en rigtig test-linje til filen, så vi kan se om selve write-adgangen virker.")

if st.button("Kør test-skrivning nu"):
    tidsstempel = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ny_linje = f"{tidsstempel},diagnose_script,Test,Automatisk diagnosticeringstest\n"

    content_opdateret = content
    if content_opdateret and not content_opdateret.endswith('\n'):
        content_opdateret += '\n'
    content_opdateret += ny_linje

    payload = {
        "message": "Diagnose: testskrivning",
        "content": base64.b64encode(content_opdateret.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }

    r4 = requests.put(
        f"https://api.github.com/repos/{REPO}/contents/{PATH}",
        headers=headers,
        json=payload
    )

    if r4.status_code in (200, 201):
        st.success("✅ Test-skrivning lykkedes! Skrivning til GitHub virker altså fint fra denne app.")
        st.json(r4.json().get("commit", {}))
        st.info("Det betyder at problemet ikke er token/repo/adgang generelt – men noget specifikt i selve app-koden, der kalder save_action_log forkert et sted, eller ikke kalder den længere.")
    else:
        st.error(f"❌ Test-skrivning fejlede. Status: {r4.status_code}")
        st.code(r4.text)
        if r4.status_code == 403:
            st.info("403 betyder ofte: tokenet mangler 'contents: write' rettighed, eller I har ramt et rate limit.")
        elif r4.status_code == 409:
            st.info("409 betyder SHA-konflikt – filen er ændret siden vi hentede den. Prøv at genindlæse siden og kør testen igen.")
        elif r4.status_code == 422:
            st.info("422 betyder ugyldigt payload – kunne tyde på encoding-problemer.")
