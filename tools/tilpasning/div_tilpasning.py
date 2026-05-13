import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO

# --- 1. CONFIGURATION ---
REPO = "Kamudinho/HIF-data"
OVERWRITE_DB_PATH = "data/players/1div_overskrivning.csv" 
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

POS_TRANSLATIONS = {
    "Center Back": "Midterforsvarer", "Left Back": "Venstre Back", "Right Back": "Højre Back",
    "Left Wing Back": "Venstre Wingback", "Right Wing Back": "Højre Wingback",
    "Defensive Midfielder": "Defensiv Midtbane", "Central Midfielder": "Central Midtbane",
    "Attacking Midfielder": "Offensiv Midtbane", "Left Midfielder": "Venstre Midtbane",
    "Right Midfielder": "Højre Midtbane", "Forward": "Angriber", "Left Winger": "Venstre kant",
    "Right Winger": "Højre kant", "Goalkeeper": "Målmand", "Defender": "Forsvarsspiller",
    "Midfielder": "Midtbanespiller"
}

# --- 2. GITHUB SERVICE ---
def get_github_file(path):
    try:
        import time
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Cache-Control": "no-cache"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8-sig', errors='replace')
            return content, data['sha']
    except Exception as e:
        st.error(f"GitHub fejl: {e}")
    return None, None

def save_to_github(df):
    with st.spinner("Uploader til GitHub..."):
        try:
            _, sha = get_github_file(OVERWRITE_DB_PATH)
            csv_content = df.to_csv(index=False, encoding='utf-8-sig')
            payload = {
                "message": "Bulk update 1div data", 
                "content": base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'), 
                "sha": sha
            }
            r = requests.put(f"https://api.github.com/repos/{REPO}/contents/{OVERWRITE_DB_PATH}", 
                             headers={"Authorization": f"token {GITHUB_TOKEN}"}, json=payload)
            if r.status_code in [200, 201]:
                st.success("Alle ændringer er nu gemt på GitHub!")
                return True
        except Exception as e:
            st.error(f"Gemme-fejl: {e}")
    return False

def vis_side():
    st.title("Sikker Editor: 1. Division")
    
    # --- INDLÆSNING ---
    if 'full_df_1div' not in st.session_state:
        content, _ = get_github_file(OVERWRITE_DB_PATH)
        if content:
            df = pd.read_csv(StringIO(content), encoding='utf-8-sig')
            df.columns = df.columns.str.upper().str.strip()
            if 'PLAYER_WYID' in df.columns:
                df['PLAYER_WYID'] = pd.to_numeric(df['PLAYER_WYID'], errors='coerce').fillna(0).astype(int)
            st.session_state['full_df_1div'] = df
        else: return

    df = st.session_state['full_df_1div'].copy()

    # --- STATISTIK ---
    mangler_opta = df[(df['PLAYER_OPTAUUID'].isna()) | (df['PLAYER_OPTAUUID'].astype(str).str.lower() == "none") | (df['PLAYER_OPTAUUID'].astype(str).str.strip() == "")].shape[0]
    uden_klub = df[(df['KLUB'].isna()) | (df['KLUB'].astype(str).str.lower() == "none") | (df['KLUB'].astype(str).str.strip() == "")].shape[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Mangler Opta-ID", mangler_opta)
    c2.metric("Uden klub", uden_klub)
    c3.metric("Total spillere", len(df))

    st.divider()

    # --- SØGNING ---
    soegning = st.text_input("Søg spiller/klub:", key="search").strip().lower()
    if len(soegning) >= 2:
        mask = df.apply(lambda x: x.astype(str).str.lower().str.contains(soegning)).any(axis=1)
        visnings_df = df[mask].copy().reset_index(drop=True)
    else:
        visnings_df = df.copy().reset_index(drop=True)

    # --- EDITOR ---
    # Bemærk: Vi bruger IKKE on_change her for at undgå rerun ved hver celle
    edited_data = st.data_editor(
        visnings_df,
        height=600,
        use_container_width=True,
        hide_index=True,
        disabled=["PLAYER_WYID"], 
        key="spiller_editor",
        column_config={
            "PLAYER_WYID": st.column_config.NumberColumn("WYID (Låst)", format="%d"),
            "COMPETITION_WYID": st.column_config.NumberColumn("Komp-ID", format="%d"),
            "POSITION": st.column_config.SelectboxColumn("Position", options=list(POS_TRANSLATIONS.values())),
        }
    )

    # --- GEM-KNAP ---
    # Vi tjekker om der er lavet ændringer i editoren
    if st.session_state.spiller_editor["edited_rows"]:
        st.warning("Du har ugemte ændringer i tabellen!")
        
        if st.button("💾 Gem alle ændringer til GitHub", type="primary", use_container_width=True):
            # 1. Hent ændringerne fra editoren
            changes = st.session_state.spiller_editor["edited_rows"]
            
            # 2. Opdater master-datasættet i session_state
            for idx_str, updated_cols in changes.items():
                row_idx = int(idx_str)
                wyid = visnings_df.iloc[row_idx]['PLAYER_WYID']
                
                # Find rækken i det fulde datasæt og opdater
                full_df_idx = df[df['PLAYER_WYID'] == wyid].index
                if not full_df_idx.empty:
                    for col, val in updated_cols.items():
                        df.at[full_df_idx[0], col] = val
            
            # 3. Gem til GitHub
            if save_to_github(df):
                st.session_state['full_df_1div'] = df
                st.cache_data.clear()
                # Vi venter et kort øjeblik og genindlæser så tallene passer
                st.rerun()

if __name__ == "__main__":
    vis_side()
