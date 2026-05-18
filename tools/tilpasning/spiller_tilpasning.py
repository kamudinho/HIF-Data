import streamlit as st
import pandas as pd
import requests
import base64
import os
from io import StringIO

# --- 1. CONFIGURATION & GITHUB CONFIG (Genbrugt fra din anden side) ---
REPO = "Kamudinho/HIF-data"
OVERWRITE_DB_PATH = "data/players/1div_overskrivning.csv"
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]

# De præcise, godkendte oversættelser (sikrer at rå engelske værdier bliver til pænt dansk)
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
    """
    Oversætter ødelagte UTF-8/ANSI tegn (danske og baltiske/østlige tegn) 
    til deres rigtige bogstaver.
    """
    if not isinstance(val, str):
        return val
        
    tegn_map = {
        # Danske tegn
        '√∏': 'ø', '√ò': 'Ø',
        '√¶': 'æ', '√Ü': 'Æ',
        '√•': 'å', '√Ö': 'Å',
        '√†': 'å',
        '√∫': 'ú',
        '≈°': 'š', '≈†': 'Š',
        '≈æ': 'ž', '≈Ω': 'Ž',
        '√≥': 'ó',
        '√©': 'é', '√®': 'è', '√¢': 'â', '√º': 'ü', '√∂': 'ö', '√§': 'ä'
    }
    
    for grimt, godt in tegn_map.items():
        val = val.replace(grimt, godt)
        
    if "√∏" in val or "√¶" in val or "√•" in val:
        val = val.replace("√∏", "ø").replace("√¶", "æ").replace("√•", "å")
        
    return val

# --- 2. GITHUB DATA SERVICE ---
def get_github_file(path):
    try:
        import time
        timestamp = int(time.time())
        url = f"https://api.github.com/repos/{REPO}/contents/{path}?t={timestamp}"
        
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            content = base64.b64decode(data['content']).decode('utf-8-sig', errors='replace')
            return content, data['sha']
    except Exception as e:
        st.error(f"Fejl ved live-hentning fra GitHub: {e}")
    return None, None

def save_to_github(df):
    try:
        # Hent den nyeste SHA for at undgå merge-fejl (conflict 409)
        _, sha = get_github_file(OVERWRITE_DB_PATH)
        
        # Sørg for at gemme med præcis kolonne-struktur
        original_cols = ['NAVN', 'POSITION', 'KLUB', 'PLAYER_WYID', 'PLAYER_OPTAUUID', 'COMPETITION_WYID', 'COMPETITION_OPTAUUID']
        export_df = df[original_cols].copy()
        
        # Sørg for ID'er står som pæne strenge/heltal
        for id_col in ['PLAYER_WYID', 'COMPETITION_WYID']:
            if id_col in export_df.columns:
                export_df[id_col] = export_df[id_col].astype(str).replace(r'\.0$', '', regex=True)
        
        # Eksporter til CSV med den korrekte encoding
        csv_content = export_df.to_csv(index=False, encoding='utf-8-sig')
        
        payload = {
            "message": "Auto-update spiller_overskrivning (Specialtegn & data-rettelser)", 
            "content": base64.b64encode(csv_content.encode('utf-8')).decode('utf-8'), 
            "sha": sha
        }
        
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        r = requests.put(
            f"https://api.github.com/repos/{REPO}/contents/{OVERWRITE_DB_PATH}", 
            headers=headers, 
            json=payload
        )
        
        if r.status_code in [200, 201]:
            st.toast("Data gemt", icon="✅")
            return True
        else:
            st.error(f"Fejl ved opdatering af data! (Status {r.status_code}): {r.text}")
    except Exception as e:
        st.error(f"Fejl ved automatisk gem: {e}")
    return False

# --- 3. AUTO-SAVE HANDLER (Svarende til din anden side) ---
def handle_auto_save():
    """
    Køres automatisk via on_change på st.data_editor.
    """
    if 'spiller_editor' in st.session_state and st.session_state['spiller_editor'].get("edited_rows"):
        changes = st.session_state['spiller_editor']["edited_rows"]
        full_df = st.session_state['full_df_editor'].copy()
        visnings_df = st.session_state['visnings_df_editor'].copy()
        
        # Flag for at se om der rent faktisk er lavet ændringer
        has_changed = False
        
        for idx_str, updated_cols in changes.items():
            row_idx = int(idx_str)
            
            # Find den korrekte spiller i den kilde-tabel (som kan være filtreret)
            wyid = visnings_df.iloc[row_idx]['PLAYER_WYID']
            
            # Find og opdater spilleren i det fulde datasæt
            idx_in_full = full_df[full_df['PLAYER_WYID'] == wyid].index
            if not idx_in_full.empty:
                has_changed = True
                for col, val in updated_cols.items():
                    # Hvis vi gemmer en ændret position, gemmer vi den som valgt
                    full_df.at[idx_in_full[0], col] = val

        if has_changed:
            # Opdater hukommelsen med det samme
            st.session_state['full_df_editor'] = full_df
            
            # Skub opdateringerne direkte op på din GitHub!
            if save_to_github(full_df):
                st.session_state['spiller_editor']["edited_rows"] = {}
                # Ryd Streamlits cache og genindlæs siden så ændringerne træder i kraft
                st.cache_data.clear()
                st.rerun()

def vis_side():
    st.caption(
        "Her kan du rette navn, position og klub direkte i tabellen. "
        "De tekniske ID-kolonner (Wyscout, Opta og turneringer) er låst for at beskytte dataforbindelsen."
    )

    # --- 1. INDLÆS FRA GITHUB (Cache-beskyttet ligesom din anden side) ---
    if 'full_df_editor' not in st.session_state:
        content, _ = get_github_file(OVERWRITE_DB_PATH)
        if content is None: 
            st.error("Kunne ikke hente spiller_overskrivning.csv fra GitHub.")
            return
        
        df = pd.read_csv(StringIO(content), encoding='utf-8-sig')
        
        # Standardiser kolonner til UPPERCASE
        df.columns = df.columns.str.upper().str.strip()
        
        # Standardiser kolonner
        for col in ['NAVN', 'POSITION', 'KLUB', 'PLAYER_WYID', 'PLAYER_OPTAUUID', 'COMPETITION_WYID', 'COMPETITION_OPTAUUID']:
            if col not in df.columns:
                df[col] = ""
                
        # Rens specialtegn i hukommelsen
        for col in ['NAVN', 'KLUB', 'POSITION']:
            df[col] = df[col].fillna("").astype(str).apply(rens_specialtegn).str.strip()
            
        # OVERSÆT MANDATORISK: Gør rå engelske ord til pæne danske værdier i editoren
        df['POSITION'] = df['POSITION'].replace(POS_TRANSLATIONS)
            
        st.session_state['full_df_editor'] = df.copy()
    else:
        df = st.session_state['full_df_editor'].copy()

    # --- 2. SØGEFELT (Taster live med JavaScript-trigger) ---
    soegning = st.text_input(
        "Søg på navn, position eller klub (søgningen starter efter 2 tegn):", 
        key="live_search_field"
    ).strip().lower()

    # --- JAVASCRIPT TRIGGER (Sikrer live søgning uden Enter) ---
    st.components.v1.html(
        """
        <script>
        const doc = window.parent.document;
        const inputs = doc.querySelectorAll('input[type="text"]');
        inputs.forEach(input => {
            if (input.getAttribute('aria-label') && input.getAttribute('aria-label').includes('Søg på navn')) {
                if (!input.dataset.hasLiveListener) {
                    input.addEventListener('input', (e) => {
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    });
                    input.dataset.hasLiveListener = "true";
                }
            }
        });
        </script>
        """,
        height=0,
    )

    # --- 3. SØGE-FILTRERING ---
    if len(soegning) >= 2:
        navn_match = df['NAVN'].fillna("").astype(str).str.lower().str.contains(soegning)
        pos_match = df['POSITION'].fillna("").astype(str).str.lower().str.contains(soegning)
        klub_match = df['KLUB'].fillna("").astype(str).str.lower().str.contains(soegning)
        
        visnings_df = df[navn_match | pos_match | klub_match].copy().reset_index(drop=True)
    else:
        visnings_df = df.copy().reset_index(drop=True)

    # Gem visningen midlertidigt i session state, så handle_auto_save kan regne række-indekset ud
    st.session_state['visnings_df_editor'] = visnings_df.copy()

    # --- 4. DATA_EDITOR MED AUTO-SAVE-CALLBACK ---
    # Vi sammensætter en skudsikker liste af tilladte positionsværdier, inkl. de engelske termer hvis de optræder.
    options_liste = [
        "Målmand", "Goalkeeper",
        "Forsvarsspiller", "Defender", "Stopper", "Center Back", "Left Back", "Right Back", "Venstre back", "Højre Back",
        "Venstre Wingback", "Left Wing Back", "Højre Wingback", "Right Wing Back",
        "Midtbanespiller", "Midfielder", "Defensiv midtbane", "Defensive Midfielder", "Central midtbane", "Central Midfielder", 
        "Offensiv midtbane", "Attacking Midfielder", "Venstre midtbane", "Left Midfielder", "Højre midtbane", "Right Midfielder",
        "Angriber", "Forward", "Venstre kant", "Left Winger", "Højre kant", "Right Winger"
    ]

    st.data_editor(
        visnings_df,
        height=600,
        num_rows="fixed",
        use_container_width=True,
        hide_index=True,
        disabled=["PLAYER_WYID", "PLAYER_OPTAUUID", "COMPETITION_WYID", "COMPETITION_OPTAUUID"],
        key="spiller_editor",
        on_change=handle_auto_save, # Auto-gemmer med det samme, når du redigerer en række!
        column_config={
            "NAVN": st.column_config.TextColumn(
                "Navn",
                help="Rediger spillerens navn",
                required=True
            ),
            "POSITION": st.column_config.SelectboxColumn(
                "Position",
                help="Vælg position",
                options=options_liste,
                required=True
            ),
            "KLUB": st.column_config.TextColumn(
                "Klub",
                help="Rediger spillerens nuværende klub",
                required=True
            ),
            "PLAYER_WYID": st.column_config.NumberColumn(
                "PLAYER_WYID",
                format="%d"
            ),
            "PLAYER_OPTAUUID": st.column_config.TextColumn(
                "PLAYER-UUID"
            ),
            "COMPETITION_WYID": st.column_config.NumberColumn(
                "Turnering-WYID",
                format="%d"
            ),
            "COMPETITION_OPTAUUID": st.column_config.TextColumn(
                "Turnering-UUID"
            )
        }
    )

if __name__ == "__main__":
    vis_side()
