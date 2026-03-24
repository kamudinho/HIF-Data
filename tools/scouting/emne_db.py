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

def rens_id(val):
    if pd.isna(val) or str(val).strip() == "": return ""
    return str(val).split('.')[0].strip()

def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8')
        return content
    return None

@st.dialog("Spillerprofil: Emne", width="large")
def vis_emne_modal(valgt_navn, emne_data, alle_scout_rapporter, career_df, billed_map):
    # Hent nyeste info fra emnelisten
    nyeste = emne_data[emne_data['Navn'] == valgt_navn].iloc[0]
    
    # Prøv at finde historiske scout-rapporter (hvis de findes i scouting_db.csv)
    rapporter = alle_scout_rapporter[alle_scout_rapporter['Navn'] == valgt_navn] if alle_scout_rapporter is not None else pd.DataFrame()
    
    pid = "" # Vi forsøger at udlede ID hvis muligt via billed_map eller rapporter
    img_url = "https://cdn.pixabay.com/photo/2016/08/08/09/17/avatar-1577909_1280.png"
    
    # Header
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        st.image(img_url, width=120)
    with c2:
        st.subheader(valgt_navn)
        st.write(f"**Klub:** {nyeste.get('Klub', '-')}")
        st.write(f"**Status:** {nyeste.get('Prioritet', '-')} ({nyeste.get('Pos_Prioritet', '-')})")
    with c3:
        st.metric("Pos (Tal)", nyeste.get('Pos_Tal', '-'))
        st.write(f"**Løn:** {nyeste.get('Lon', '-')}")

    t1, t2, t3 = st.tabs(["Emne Detaljer", "Scout Historik", "Sæsonstats"])

    # --- TAB 1: EMNE DETALJER ---
    with t1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.info(f"**Bemærkning:**\n\n{nyeste.get('Bemaerkning', '-')}")
        with col_b:
            st.write(f"**Forventning:** {nyeste.get('Forventning', '-')}")
            st.write(f"**Kontraktudløb:** {nyeste.get('Kontrakt', '-')}")
            st.write(f"**Oprettet af:** {nyeste.get('Oprettet_af', '-')}")
            st.write(f"**Dato tilføjet:** {nyeste.get('Dato', '-')}")

    # --- TAB 2: SCOUT HISTORIK (Fra scouting_db) ---
    with t2:
        if not rapporter.empty:
            for _, r in rapporter.sort_values('Dato', ascending=False).iterrows():
                with st.expander(f"Rapport d. {r['Dato']} (Rating: {r.get('Rating_Avg', '-')})"):
                    st.write(f"**Vurdering:** {r.get('Vurdering', '-')}")
                    st.write(f"**Styrker:** {r.get('Styrker', '-')}")
        else:
            st.info("Der er endnu ikke oprettet dybdegående scout-rapporter på dette emne.")

    # --- TAB 3: SÆSONSTATS ---
    with t3:
        st.info("Wyscout data indlæses her...")
        # (Samme career_df logik som i din original kan indsættes her)

def vis_side(dp):
    st.subheader("📋 Strategisk Emneliste (Database)")

    # 1. HENT DATA FRA GITHUB
    content = get_github_file(FILE_PATH)
    if not content:
        st.warning("Kunne ikke hente emneliste.csv fra GitHub.")
        return

    df_emner = pd.read_csv(StringIO(content))
    
    # 2. HENT SCOUT RAPPORTER (til historik i modal)
    # Her antager vi at scouting_db.csv findes i dp eller hentes analogt
    df_rapporter = None
    scout_content = get_github_file("data/scouting_db.csv")
    if scout_content:
        df_rapporter = pd.read_csv(StringIO(scout_content))

    # 3. FORBERED DISPLAY
    if df_emner.empty:
        st.info("Emnelisten er tom.")
        return

    # Sortering: Prioritet (A øverst) og derefter Positionstal
    df_emner = df_emner.sort_values(['Pos_Prioritet', 'Pos_Tal'], ascending=[True, True])

    df_display = df_emner[['Navn', 'Position', 'Klub', 'Pos_Tal', 'Pos_Prioritet', 'Prioritet', 'Kontrakt']].copy()
    df_display.insert(0, "Se", False)

    # 4. TABEL VISNING
    dynamic_height = (len(df_display) + 1) * 35 + 10
    
    ed_result = st.data_editor(
        df_display,
        column_config={
            "Se": st.column_config.CheckboxColumn("Profil", default=False),
            "Pos_Tal": st.column_config.TextColumn("POS"),
            "Pos_Prioritet": st.column_config.TextColumn("Kat."),
            "Prioritet": st.column_config.TextColumn("Status"),
        },
        disabled=df_display.columns.drop("Se"),
        hide_index=True,
        use_container_width=True,
        height=dynamic_height,
        key="emne_db_editor"
    )

    # 5. MODAL TRIGGER
    valgte = ed_result[ed_result["Se"] == True]
    if not valgte.empty:
        valgt_navn = valgte.iloc[-1]['Navn']
        # Vi nulstiller "Se" ved at køre rerun (hvis nødvendigt) eller kalder modal direkte
        vis_emne_modal(valgt_navn, df_emner, df_rapporter, None, {})
