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

def repair_encoding(text):
    if not isinstance(text, str): return text
    try:
        return text.encode('latin1').decode('utf-8')
    except:
        return text

# --- 2. GITHUB SERVICE ---
def get_github_file(path):
    try:
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
                "message": "Update 1div: KPI, Dubletter & Position fix",
                "content": base64.b64encode(csv_content.encode('utf-8-sig')).decode('utf-8'),
                "sha": sha
            }
            r = requests.put(
                f"https://api.github.com/repos/{REPO}/contents/{OVERWRITE_DB_PATH}",
                headers={"Authorization": f"token {GITHUB_TOKEN}"}, 
                json=payload
            )
            return r.status_code in [200, 201]
        except Exception as e:
            st.error(f"Fejl ved upload: {e}")
    return False

def vis_side():
    st.set_page_config(layout="wide", page_title="HIF 1. Div Editor")
    st.title("Sikker Editor: 1. Division")
    
    if 'full_df_1div' not in st.session_state:
        content, _ = get_github_file(OVERWRITE_DB_PATH)
        if content:
            df = pd.read_csv(StringIO(content))
            df.columns = df.columns.str.upper().str.strip()
            
            # Rens Navne
            if 'NAVN' in df.columns:
                df['NAVN'] = df['NAVN'].apply(repair_encoding)
            
            # FIX: Oversæt positioner med det samme (så de ikke er blanke i editor)
            if 'POSITION' in df.columns:
                df['POSITION'] = df['POSITION'].str.strip().map(POS_TRANSLATIONS).fillna(df['POSITION'])
            
            if 'PLAYER_WYID' in df.columns:
                df['PLAYER_WYID'] = pd.to_numeric(df['PLAYER_WYID'], errors='coerce').fillna(0).astype(int)
            
            st.session_state['full_df_1div'] = df
        else: 
            st.error("Kunne ikke hente data.")
            return

    df = st.session_state['full_df_1div'].copy()

    # --- 3. DUBLET- OG FEJL-IDENTIFIKATION ---
    mangler_opta = df[(df['PLAYER_OPTAUUID'].isna()) | (df['PLAYER_OPTAUUID'].astype(str).str.lower() == "none")].shape[0]
    error_list = []
    dublet_mask = pd.Series([False] * len(df))

    # Tjekker for dubletter i nøgle-kolonner
    for col in ['NAVN', 'PLAYER_WYID', 'PLAYER_OPTAUUID']:
        clean_series = df[col].replace(["None", "none", "", 0, "0"], pd.NA)
        dupes = clean_series[clean_series.duplicated(keep=False) & clean_series.notna()].unique()
        for val in dupes:
            names = df[df[col] == val]['NAVN'].tolist()
            error_list.append(f"**{col} Dublet ({val}):** {', '.join(names)}")
            # Markér rækkerne til filteret
            idx_to_mark = df[df[col] == val].index
            for i in idx_to_mark: dublet_mask[i] = True

    # --- 4. KPI DASHBOARD ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Mangler Opta-ID", mangler_opta)
    c2.metric("Dublet-konflikter", len(error_list))
    c3.metric("Total spillere", len(df))

    if error_list:
        with st.expander("⚠️ Dublet-fejl fundet (Klik for detaljer)", expanded=True):
            for err in error_list: st.write(f"- {err}")

    st.divider()

    # --- 5. SØGNING & FILTER ---
    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        soegning = st.text_input("Søg spiller, klub eller ID:").strip().lower()
    with col_s2:
        st.write(" ") # Spacer
        vis_kun_dubletter = st.toggle("Vis kun dubletter / fejl")

    visnings_df = df.copy()
    if vis_kun_dubletter: 
        visnings_df = visnings_df[dublet_mask]
        
    if len(soegning) >= 2:
        mask = visnings_df.apply(lambda x: x.astype(str).str.lower().str.contains(soegning)).any(axis=1)
        visnings_df = visnings_df[mask]

    # --- 6. EDITOR ---
    pos_options = sorted(list(POS_TRANSLATIONS.values()))

    edited_df = st.data_editor(
        visnings_df,
        height=550,
        use_container_width=True,
        hide_index=True,
        disabled=["PLAYER_WYID"], 
        key="spiller_editor",
        column_config={
            "PLAYER_WYID": st.column_config.NumberColumn("WYID", format="%d"),
            "POSITION": st.column_config.SelectboxColumn("Position", options=pos_options),
            "PLAYER_OPTAUUID": st.column_config.TextColumn("Opta UUID"),
            "TEAM_WYID": st.column_config.NumberColumn("Klub WYID", format="%d"),
        }
    )

    # --- 7. GEM LOGIK ---
    if st.session_state.spiller_editor["edited_rows"]:
        if st.button("💾 Gem alle ændringer til GitHub", type="primary", use_container_width=True):
            changes = st.session_state.spiller_editor["edited_rows"]
            
            # Opdater de rigtige rækker i det store dataframe
            for idx_str, updated_cols in changes.items():
                # Vi bruger WYID til at finde den præcise række i session_state
                rel_idx = int(idx_str)
                wyid = visnings_df.iloc[rel_idx]['PLAYER_WYID']
                
                for col, val in updated_cols.items():
                    df.loc[df['PLAYER_WYID'] == wyid, col] = val
            
            if save_to_github(df):
                st.session_state['full_df_1div'] = df
                st.success("Data er gemt succesfuldt!")
                time.sleep(1)
                st.rerun()

if __name__ == "__main__":
    vis_side()
