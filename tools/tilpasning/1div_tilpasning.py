import streamlit as st
import pandas as pd
import requests
import base64
import os
from io import StringIO

# --- 1. CONFIGURATION & GITHUB CONFIG ---
REPO = "Kamudinho/HIF-data"
# Sti opdateret til din 1. division fil
OVERWRITE_DB_PATH = "data/players/1div_overskrivning.csv" 
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

POS_TRANSLATIONS = {
    "Center Back": "Midterforsvarer",
    "Left Back": "Venstre Back",
    "Right Back": "Højre Back",
    "Left Wing Back": "Venstre Wingback",
    "Right Wing Back": "Højre Wingback",
    "Defensive Midfielder": "Defensiv Midtbane",
    "Central Midfielder": "Central Midtbane",
    "Attacking Midfielder": "Offensiv Midtbane",
    "Left Midfielder": "Venstre Midtbane",
    "Right Midfielder": "Højre Midtbane",
    "Forward": "Angriber",
    "Left Winger": "Venstre kant",
    "Right Winger": "Højre kant",
    "Goalkeeper": "Målmand",
    "Defender": "Forsvarsspiller",
    "Midfielder": "Midtbanespiller"
}

def rens_specialtegn(val):
    if not isinstance(val, str):
        return val
    tegn_map = {
        '√∏': 'ø', '√ò': 'Ø', '√¶': 'æ', '√Ü': 'Æ', '√•': 'å', '√Ö': 'Å',
        '√†': 'å', '√∫': 'ú', '≈°': 'š', '≈†': 'Š', '≈æ': 'ž', '≈Ω': 'Ž',
        '√≥': 'ó', '√©': 'é', '√®': 'è', '√¢': 'â', '√º': 'ü', '√∂': 'ö', '√§': 'ä'
    }
    for grimt, godt in tegn_map.items():
        val = val.replace(grimt, godt)
    return val

# --- 2. GITHUB DATA SERVICE ---
def get_github_file(path):
    try:
        import time
        timestamp = int(time.time())
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={timestamp}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Cache-Control": "no-cache"
        }
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8-sig', errors='replace')
            return content, data['sha']
    except Exception as e:
        st.error(f"Fejl ved hentning: {e}")
    return None, None

def save_to_github(df):
    try:
        _, sha = get_github_file(OVERWRITE_DB_PATH)
        
        # Vi gemmer alle tilgængelige kolonner
        export_df = df.copy()
        
        # Formatering af ID-kolonner så de ikke gemmes som 12345.0
        for col in export_df.columns:
            if "WYID" in col or "ID" in col:
                export_df[col] = export_df[col].astype(str).replace(r'\.0$', '', regex=True).replace('nan', '')

        csv_content = export_df.to_csv(index=False, encoding='utf-8-sig')
        payload = {
            "message": "Manuel opdatering af 1div_overskrivning", 
            "content": base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'), 
            "sha": sha
        }
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{OVERWRITE_DB_PATH}", headers=headers, json=payload)
        
        if r.status_code in [200, 201]:
            st.toast("Ændringer gemt i 1. division databasen", icon="✅")
            return True
    except Exception as e:
        st.error(f"Fejl ved gem: {e}")
    return False

# --- 3. AUTO-SAVE HANDLER ---
def handle_auto_save():
    if 'spiller_editor' in st.session_state and st.session_state['spiller_editor'].get("edited_rows"):
        changes = st.session_state['spiller_editor']["edited_rows"]
        full_df = st.session_state['full_df_1div'].copy()
        visnings_df = st.session_state['visnings_df_1div'].copy()
        
        has_changed = False
        for idx_str, updated_cols in changes.items():
            row_idx = int(idx_str)
            # Vi bruger PLAYER_WYID som nøgle til at finde rækken i det fulde datasæt
            wyid = visnings_df.iloc[row_idx]['PLAYER_WYID']
            idx_in_full = full_df[full_df['PLAYER_WYID'] == wyid].index
            
            if not idx_in_full.empty:
                has_changed = True
                for col, val in updated_cols.items():
                    full_df.at[idx_in_full[0], col] = val

        if has_changed:
            st.session_state['full_df_1div'] = full_df
            if save_to_github(full_df):
                st.session_state['spiller_editor']["edited_rows"] = {}
                st.cache_data.clear()
                st.rerun()

def vis_side():
    st.title("Editor: 1. Division Overskrivning")
    st.info("Som administrator kan du rette i alle celler. Ændringer gemmes automatisk på GitHub ved redigering.")

    # --- INDLÆS DATA ---
    if 'full_df_1div' not in st.session_state:
        content, _ = get_github_file(OVERWRITE_DB_PATH)
        if content:
            df = pd.read_csv(StringIO(content), encoding='utf-8-sig')
            df.columns = df.columns.str.upper().str.strip()
            
            # Rens data
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].fillna("").astype(str).apply(rens_specialtegn).str.strip()
            
            # Oversæt positioner til visning
            if 'POSITION' in df.columns:
                df['POSITION'] = df['POSITION'].replace(POS_TRANSLATIONS)
                
            st.session_state['full_df_1div'] = df.copy()
        else:
            st.error("Kunne ikke finde filen på GitHub.")
            return

    df = st.session_state['full_df_1div']

    # --- SØGEFELT ---
    soegning = st.text_input("Søg i databasen:", key="search_1div").strip().lower()

    # Live-search script
    st.components.v1.html("""
        <script>
        const doc = window.parent.document;
        const inputs = doc.querySelectorAll('input[type="text"]');
        inputs.forEach(input => {
            if (!input.dataset.hasLiveListener) {
                input.addEventListener('input', () => input.dispatchEvent(new Event('change', { bubbles: true })));
                input.dataset.hasLiveListener = "true";
            }
        });
        </script>
        """, height=0)

    # Filtrering
    if len(soegning) >= 2:
        mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(soegning)).any(axis=1)
        visnings_df = df[mask].copy().reset_index(drop=True)
    else:
        visnings_df = df.copy().reset_index(drop=True)

    st.session_state['visnings_df_1div'] = visnings_df

    # --- DATA EDITOR (Alle celler er åbne) ---
    st.data_editor(
        visnings_df,
        height=650,
        use_container_width=True,
        hide_index=True,
        disabled=[], # TOM LISTE = Alle celler kan redigeres
        key="spiller_editor",
        on_change=handle_auto_save,
        column_config={
            "PLAYER_WYID": st.column_config.TextColumn("WYID"),
            "COMPETITION_WYID": st.column_config.TextColumn("Komp-ID"),
            "POSITION": st.column_config.SelectboxColumn("Position", options=list(POS_TRANSLATIONS.values()) + list(POS_TRANSLATIONS.keys()))
        }
    )

if __name__ == "__main__":
    vis_side()
