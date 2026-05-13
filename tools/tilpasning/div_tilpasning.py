import streamlit as st
import pandas as pd
import requests
import base64
import os
from io import StringIO

# --- 1. CONFIGURATION & GITHUB CONFIG ---
REPO = "Kamudinho/HIF-data"
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
        export_df = df.copy()
        
        # Sørg for ID'er gemmes som rene tal-strenge uden .0
        for col in export_df.columns:
            if "WYID" in col or "ID" in col:
                export_df[col] = pd.to_numeric(export_df[col], errors='coerce').fillna(0).astype(int).astype(str)

        csv_content = export_df.to_csv(index=False, encoding='utf-8-sig')
        payload = {
            "message": "Manuel opdatering af 1div_overskrivning", 
            "content": base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'), 
            "sha": sha
        }
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{OVERWRITE_DB_PATH}", headers=headers, json=payload)
        
        if r.status_code in [200, 201]:
            st.toast("Ændringer gemt!", icon="✅")
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
    st.title("Editor: 1. Division")
    st.caption("Alle felter kan redigeres. Ændringer uploades direkte til GitHub.")

    # --- INDLÆS DATA ---
    if 'full_df_1div' not in st.session_state:
        content, _ = get_github_file(OVERWRITE_DB_PATH)
        if content:
            df = pd.read_csv(StringIO(content), encoding='utf-8-sig')
            df.columns = df.columns.str.upper().str.strip()
            
            # Konvertér ID-kolonner til int med det samme for at undgå editor-fejl
            for col in ['PLAYER_WYID', 'COMPETITION_WYID']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

            # Rens tekst-felter
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].fillna("").astype(str).apply(rens_specialtegn).str.strip()
            
            if 'POSITION' in df.columns:
                df['POSITION'] = df['POSITION'].replace(POS_TRANSLATIONS)
                
            st.session_state['full_df_1div'] = df.copy()
        else:
            st.error("Kunne ikke hente filen.")
            return

    df = st.session_state['full_df_1div']

    # --- SØGEFILT ---
    soegning = st.text_input("Søg (navn, ID, klub):", key="search_1div").strip().lower()

    if len(soegning) >= 2:
        mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(soegning)).any(axis=1)
        visnings_df = df[mask].copy().reset_index(drop=True)
    else:
        visnings_df = df.copy().reset_index(drop=True)

    st.session_state['visnings_df_1div'] = visnings_df

    # --- DATA EDITOR ---
    options_liste = list(POS_TRANSLATIONS.values()) + sorted(list(set(df['POSITION'].unique())))

    st.data_editor(
        visnings_df,
        height=650,
        use_container_width=True,
        hide_index=True,
        disabled=[], # Låser intet
        key="spiller_editor",
        on_change=handle_auto_save,
        column_config={
            "PLAYER_WYID": st.column_config.NumberColumn("WYID", format="%d"),
            "COMPETITION_WYID": st.column_config.NumberColumn("Komp-ID", format="%d"),
            "POSITION": st.column_config.SelectboxColumn("Position", options=options_liste),
            "NAVN": st.column_config.TextColumn("Navn", required=True),
            "KLUB": st.column_config.TextColumn("Klub"),
            "PLAYER_OPTAUUID": st.column_config.TextColumn("PLAYER-UUID"),
            "COMPETITION_OPTAUUID": st.column_config.TextColumn("Turnering-UUID")
        }
    )

if __name__ == "__main__":
    vis_side()
