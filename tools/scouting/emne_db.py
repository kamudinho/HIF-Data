import streamlit as st
import pandas as pd
from io import StringIO
import requests
import base64
from mplsoccer import Pitch
from datetime import datetime

# --- KONFIGURATION ---
REPO = "Kamudinho/HIF-data"
DB_PATH = "data/scouting_db.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
HIF_ROD = "#df003b"

POS_OPTIONS = {
    "0": "Vælg", "1": "MM", "2": "HB", "5": "VB", "3": "HCB", "3.5": "CB", "4": "VCB",
    "6": "DM", "8": "CM", "7": "HK", "11": "VK", "10": "OM", "9": "ANG"
}

# --- GITHUB FUNKTIONER ---
def get_github_file(path):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        content = base64.b64decode(data['content']).decode('utf-8', errors='replace')
        return content, data['sha']
    return None, None

def push_to_github(path, message, content, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    r = requests.put(url, headers=headers, json=payload)
    return r.status_code

# --- DATA PREP FUNKTION ---
def load_and_prepare():
    content, sha = get_github_file(DB_PATH)
    if not content: return pd.DataFrame(), None
    
    df = pd.read_csv(StringIO(content))
    df.columns = [str(c).strip() for c in df.columns]
    
    # Sorter efter dato så de nyeste rækker "vinder" i drop_duplicates
    if 'DATO' in df.columns:
        df['DATO'] = pd.to_datetime(df['DATO'], errors='coerce')
        df = df.sort_values('DATO', ascending=False)
    
    # Konverter SKYGGEHOLD til Bool (håndterer True, TRUE, 1 osv.)
    if 'SKYGGEHOLD' in df.columns:
        df['SKYGGEHOLD'] = df['SKYGGEHOLD'].astype(str).str.upper().str.strip() == 'TRUE'
    
    return df, sha

# --- SELVE UNDERSIDEN ---
def vis_side():
    st.header("HIF Scouting | Datastyring")
    
    # Hent data
    df_raw, current_sha = load_and_prepare()
    
    if df_raw.empty:
        st.error("Kunne ikke finde data i scouting_db.csv")
        return

    # Unik liste til visning (vi vil kun se hver spiller én gang i tabellerne)
    df_display = df_raw.drop_duplicates('Navn').copy()

    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Emner", "🏠 Hvidovre IF", "📋 Skyggeliste", "🏟️ Bane"])

    is_hif = df_display['KLUB'].str.contains("Hvidovre", case=False, na=False)

    # Hjælpefunktion til at gemme ændringer tilbage til GitHub
    def gem_data(edited_df, original_subset):
        with st.spinner("Gemmer til GitHub..."):
            # Hent frisk fil + SHA lige før skrivning (undgår Conflict 409)
            raw_content, latest_sha = get_github_file(DB_PATH)
            df_to_save = pd.read_csv(StringIO(raw_content))
            
            for idx, row in edited_df.iterrows():
                p_name = original_subset.iloc[idx]['Navn']
                # Opdater ALLE rækker for spilleren (historik skal matche nuværende status)
                mask = df_to_save['Navn'].str.strip() == p_name.strip()
                df_to_save.loc[mask, 'SKYGGEHOLD'] = str(row['SKYGGEHOLD']).upper()
                if 'POS' in edited_df.columns:
                    df_to_save.loc[mask, 'POS'] = row['POS']
                if 'POS_343' in edited_df.columns:
                    df_to_save.loc[mask, ['POS_343', 'POS_433', 'POS_352']] = [row['POS_343'], row['POS_433'], row['POS_352']]

            res = push_to_github(DB_PATH, f"Update {datetime.now()}", df_to_save.to_csv(index=False), latest_sha)
            if res in [200, 201]:
                st.success("Data er gemt succesfuldt!")
                st.rerun()
            else:
                st.error(f"Fejl ved gem: {res}")

    # --- TABELVISNINGER ---
    with tab1:
        df_e = df_display[~is_hif]
        ed1 = st.data_editor(df_e[['Navn', 'KLUB', 'POS', 'SKYGGEHOLD']], 
                            hide_index=True, use_container_width=True, key="ed_emner_db",
                            column_config={"SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")})
        if st.button("Gem ændringer i Emner"): gem_data(ed1, df_e)

    with tab2:
        df_h = df_display[is_hif]
        ed2 = st.data_editor(df_h[['Navn', 'POS', 'SKYGGEHOLD']], 
                            hide_index=True, use_container_width=True, key="ed_hif_db",
                            column_config={"SKYGGEHOLD": st.column_config.CheckboxColumn("Skygge")})
        if st.button("Gem ændringer i Hvidovre"): gem_data(ed2, df_h)

    with tab3:
        df_s = df_display[df_display['SKYGGEHOLD'] == True]
        if not df_s.empty:
            ed3 = st.data_editor(df_s[['Navn', 'POS_343', 'POS_433', 'POS_352']], 
                                hide_index=True, use_container_width=True, key="ed_skygge_db",
                                column_config={
                                    "POS_343": st.column_config.SelectboxColumn("3-4-3", options=list(POS_OPTIONS.keys())),
                                    "POS_433": st.column_config.SelectboxColumn("4-3-3", options=list(POS_OPTIONS.keys())),
                                    "POS_352": st.column_config.SelectboxColumn("3-5-2", options=list(POS_OPTIONS.keys()))
                                })
            if st.button("Gem taktiske positioner"): gem_data(ed3, df_s)
        else:
            st.info("Ingen spillere markeret til Skyggelisten.")

    with tab4:
        # Banevisning (bruger samme logik som før, men med data fra scouting_db)
        df_pitch = df_display[df_display['SKYGGEHOLD'] == True]
        if not df_pitch.empty:
            pitch = Pitch(pitch_type='statsbomb', pitch_color='white', line_color='#333')
            fig, ax = pitch.draw(figsize=(10, 7))
            # (Formationstegning her...)
            st.pyplot(fig)
            st.write("Banevisning er aktiv for skyggeholdet.")

# Dette sikrer at koden kun kører hvis filen køres direkte (til test)
if __name__ == "__main__":
    vis_side()
