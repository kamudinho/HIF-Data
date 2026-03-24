import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import StringIO
import requests
import base64

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
FILE_PATH = "data/emneliste.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# --- GITHUB FUNKTIONER ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8')
        return content, data['sha']
    return None, None

def push_to_github(path, message, content, sha=None):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8')
    }
    if sha: payload["sha"] = sha
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

# --- MODAL: SPILLERPROFIL ---
@st.dialog("Spillerprofil: Emne", width="large")
def vis_emne_modal(valgt_navn, emne_data, alle_scout_rapporter):
    nyeste = emne_data[emne_data['Navn'] == valgt_navn].iloc[0]
    rapporter = alle_scout_rapporter[alle_scout_rapporter['Navn'] == valgt_navn] if alle_scout_rapporter is not None else pd.DataFrame()
    
    img_url = "https://cdn.pixabay.com/photo/2016/08/08/09/17/avatar-1577909_1280.png"
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1: st.image(img_url, width=120)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"**Klub:** {nyeste.get('Klub', '-')}")
        st.write(f"**Status:** {nyeste.get('Prioritet', '-')} ({nyeste.get('Pos_Prioritet', '-')})")
    with c3:
        st.metric("Pos (Tal)", nyeste.get('Pos_Tal', '-'))
        st.write(f"**Løn:** {nyeste.get('Lon', '-')}")

    t1, t2 = st.tabs(["Detaljer", "Scout Historik"])
    with t1:
        col_a, col_b = st.columns(2)
        col_a.info(f"**Bemærkning:**\n\n{nyeste.get('Bemaerkning', '-')}")
        col_b.write(f"**Forventning:** {nyeste.get('Forventning', '-')}")
        col_b.write(f"**Kontraktudløb:** {nyeste.get('Kontrakt', '-')}")
        col_b.write(f"**Oprettet af:** {nyeste.get('Oprettet_af', '-')}")

    with t2:
        if not rapporter.empty:
            for _, r in rapporter.sort_values('Dato', ascending=False).iterrows():
                with st.expander(f"Rapport d. {r['Dato']} (Rating: {r.get('Rating_Avg', '-')})"):
                    st.write(f"**Vurdering:** {r.get('Vurdering', '-')}")
        else:
            st.info("Ingen dybdegående rapporter fundet.")

# --- HOVEDSIDE ---
def vis_side(dp):
    # 1. HENT DATA
    content, sha = get_github_file(FILE_PATH)
    if not content:
        st.error("Kunne ikke hente emneliste.csv fra GitHub.")
        return

    df = pd.read_csv(StringIO(content))
    
    # Sikr at Skyggehold kolonnen findes og er boolean
    if 'Skyggehold' not in df.columns:
        df['Skyggehold'] = False
    df['Skyggehold'] = df['Skyggehold'].fillna(False).astype(bool)

    # 2. FILTER & SORTERING
    vis_kun_skygge = st.toggle("🛡️ Vis kun Skyggehold", value=False)
    df_filtered = df[df['Skyggehold'] == True] if vis_kun_skygge else df
    df_filtered = df_filtered.sort_values(['Pos_Tal', 'Pos_Prioritet'], ascending=[True, True])

    # 3. FORBERED TABEL TIL EDITOR
    df_display = df_filtered.copy()
    
    # Interaktions-kolonner (Ikoner)
    df_display['ℹ️'] = False  # Info profil
    df_display['🗑️'] = False  # Slet permanent
    df_display = df_display.rename(columns={'Skyggehold': '🛡️'})

    # Kolonne-rækkefølge: Info først, Data i midten, Skygge & Slet bagerst
    data_cols = ['Navn', 'Pos_Tal', 'Klub', 'Pos_Prioritet', 'Prioritet', 'Lon', 'Kontrakt']
    cols_order = ['ℹ️'] + data_cols + ['🛡️', '🗑️']
    
    dynamic_height = (len(df_display) + 1) * 35 + 20

    ed_result = st.data_editor(
        df_display[cols_order],
        column_config={
            "ℹ️": st.column_config.CheckboxColumn("Profil", help="Profil", width="small"),
            "🛡️": st.column_config.CheckboxColumn("Skyggehold", help="Skyggehold", width="small"),
            "🗑️": st.column_config.CheckboxColumn("Slet", help="Slet", width="small"),
            "Pos_Tal": "POS",
            "Pos_Prioritet": "Kat.",
            "Lon": "Løn"
        },
        disabled=data_cols,
        hide_index=True,
        use_container_width=True,
        height=dynamic_height,
        key="emne_db_editor"
    )

    # 4. LOGIK HÅNDTERING
    # A. SE PROFIL
    info_valg = ed_result[ed_result["ℹ️"] == True]
    if not info_valg.empty:
        valgt_navn = info_valg.iloc[-1]['Navn']
        scout_content, _ = get_github_file("data/scouting_db.csv")
        df_rapporter = pd.read_csv(StringIO(scout_content)) if scout_content else None
        vis_emne_modal(valgt_navn, df, df_rapporter)

    # B. SLETNING (Bagerste kolonne)
    slet_valg = ed_result[ed_result["🗑️"] == True]
    if not slet_valg.empty:
        navn_slet = slet_valg.iloc[-1]['Navn']
        st.error(f"Slet permanent: **{navn_slet}**?")
        if st.button("BEKRÆFT SLETNING"):
            df_new = df[df['Navn'] != navn_slet]
            push_to_github(FILE_PATH, f"Slettede {navn_slet}", df_new.to_csv(index=False), sha)
            st.rerun()

    # C. OPDATER SKYGGEHOLD STATUS (Næstsidste kolonne)
    if not ed_result['🛡️'].equals(df_display['🛡️']):
        for idx, row in ed_result.iterrows():
            df.loc[df['Navn'] == row['Navn'], 'Skyggehold'] = row['🛡️']
        
        push_to_github(FILE_PATH, "Opdateret Skyggehold status", df.to_csv(index=False), sha)
        st.rerun()
