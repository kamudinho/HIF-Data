import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO
import time

# --- 1. KONFIGURATION ---
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

# --- HJÆLPEFUNKTION TIL AT REDDE DANSKE BOGSTAVER ---
def repair_encoding(text):
    if not isinstance(text, str):
        return text
    try:
        # Prøver at fikse de mest gængse fejl (f.eks. N√∏rager -> Nørager)
        return text.encode('latin1').decode('utf-8')
    except:
        # Hvis den fejler, har den det nok fint i forvejen
        return text

# --- 2. GITHUB SERVICE ---
def get_github_file(path):
    try:
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={int(time.time())}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Cache-Control": "no-cache"}
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            # Vi bruger utf-8-sig for at håndtere BOM (Byte Order Mark) fra Excel/Windows
            content = base64.b64decode(data['content']).decode('utf-8-sig', errors='replace')
            return content, data['sha']
    except Exception as e:
        st.error(f"GitHub fejl: {e}")
    return None, None

def save_to_github(df):
    with st.spinner("Uploader til GitHub..."):
        try:
            _, sha = get_github_file(OVERWRITE_DB_PATH)
            # Gemmer altid med utf-8-sig, så Excel kan læse det korrekt bagefter
            csv_content = df.to_csv(index=False, encoding='utf-8-sig')
            payload = {
                "message": "Bulk update 1div data (Encoding Fix)",
                "content": base64.b64encode(csv_content.encode('utf-8-sig')).decode('utf-8'),
                "sha": sha
            }
            r = requests.put(
                f"https://api.github.com/repos/{REPO}/contents/{OVERWRITE_DB_PATH}",
                headers={"Authorization": f"token {GITHUB_TOKEN}"}, 
                json=payload
            )
            if r.status_code in [200, 201]:
                st.success("Gemt med korrekt format!")
                return True
        except Exception as e:
            st.error(f"Fejl ved upload: {e}")
    return False

def vis_side():
    st.set_page_config(layout="wide", page_title="HIF 1. Div Editor")
    st.title("Sikker Editor: 1. Division")
    
    if 'full_df_1div' not in st.session_state:
        content, _ = get_github_file(OVERWRITE_DB_PATH)
        if content:
            # Læs filen og rens med det samme
            df = pd.read_csv(StringIO(content))
            df.columns = df.columns.str.upper().str.strip()
            
            # Kør navne-vaskemaskinen på kolonnen NAVN
            if 'NAVN' in df.columns:
                df['NAVN'] = df['NAVN'].apply(repair_encoding)
            
            if 'PLAYER_WYID' in df.columns:
                df['PLAYER_WYID'] = pd.to_numeric(df['PLAYER_WYID'], errors='coerce').fillna(0).astype(int)
            
            st.session_state['full_df_1div'] = df
        else: 
            return

    df = st.session_state['full_df_1div'].copy()

    # --- KPI & FEJL-IDENTIFIKATION ---
    mangler_opta = df[(df['PLAYER_OPTAUUID'].isna()) | (df['PLAYER_OPTAUUID'].astype(str).str.lower() == "none")].shape[0]
    error_list = []
    dublet_mask = pd.Series([False] * len(df))

    for col in ['NAVN', 'PLAYER_WYID', 'PLAYER_OPTAUUID']:
        clean_series = df[col].replace(["None", "none", "", 0, "0"], pd.NA)
        dupes = clean_series[clean_series.duplicated(keep=False) & clean_series.notna()].unique()
        for val in dupes:
            names = df[df[col] == val]['NAVN'].tolist()
            error_list.append(f"**{col} Dublet ({val}):** {', '.join(names)}")
            dublet_mask = dublet_mask | (df[col] == val)

    # --- VIS KPI'ER ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Mangler Opta-ID", mangler_opta)
    c2.metric("Dublet-konflikter", len(error_list))
    c3.metric("Total spillere", len(df))

    if error_list:
        with st.expander("⚠️ Dublet-fejl fundet", expanded=True):
            for err in error_list: st.write(f"- {err}")

    st.divider()

    # --- SØGNING ---
    soegning = st.text_input("Søg spiller/klub:").strip().lower()
    vis_kun_dubletter = st.toggle("Vis kun dubletter")

    visnings_df = df.copy()
    if vis_kun_dubletter: visnings_df = visnings_df[dublet_mask]
    if len(soegning) >= 2:
        mask = visnings_df.apply(lambda x: x.astype(str).str.lower().str.contains(soegning)).any(axis=1)
        visnings_df = visnings_df[mask]

    # --- EDITOR ---
    edited_df = st.data_editor(
        visnings_df.reset_index(drop=True),
        height=500,
        use_container_width=True,
        hide_index=True,
        disabled=["PLAYER_WYID"], 
        key="spiller_editor",
        column_config={
            "PLAYER_WYID": st.column_config.NumberColumn("WYID", format="%d"),
            "POSITION": st.column_config.SelectboxColumn("Position", options=list(POS_TRANSLATIONS.values())),
        }
    )

    # --- GEM ---
    if st.session_state.spiller_editor["edited_rows"]:
        if st.button("💾 Gem ændringer (inkl. encoding fix)", type="primary", use_container_width=True):
            changes = st.session_state.spiller_editor["edited_rows"]
            for idx_str, updated_cols in changes.items():
                wyid = visnings_df.iloc[int(idx_str)]['PLAYER_WYID']
                full_df_idx = df[df['PLAYER_WYID'] == wyid].index
                if not full_df_idx.empty:
                    for col, val in updated_cols.items():
                        df.at[full_df_idx[0], col] = val
            
            if save_to_github(df):
                st.session_state['full_df_1div'] = df
                st.rerun()

if __name__ == "__main__":
    vis_side()
