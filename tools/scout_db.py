import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import requests

# --- 1. HJÆLPEFUNKTIONER ---
def find_col(df, target):
    cols = {str(c).strip().lower(): str(c) for c in df.columns}
    return cols.get(target.strip().lower())

def rens_metrik_vaerdi(val):
    try:
        if pd.isna(val) or str(val).strip() == "": return 0
        return int(float(str(val).replace(',', '.')))
    except: return 0

def hent_vaerdi_robust(row, col_name):
    # Leder i rækken efter kolonnen uanset store/små bogstaver
    row_dict = {str(k).strip().lower(): v for k, v in row.items()}
    val = row_dict.get(col_name.strip().lower(), "")
    return "" if pd.isna(val) else val

# --- DEN OPDATEREDE MAPPING (Fokuseret på POS-tal) ---
def map_position(row):
    # 1. Hent værdier og tving dem til tekst. 
    # Vi fjerner evt. decimaler (f.eks. "3.0" bliver til "3")
    pos_raw = str(hent_vaerdi_robust(row, 'POS')).strip().split('.')[0]
    role_val = str(hent_vaerdi_robust(row, 'ROLECODE3')).strip().upper()
    
    # Ordbog baseret på dine POS-tal
    pos_dict = {
        "1": "Målmand",
        "2": "Højre Back",
        "3": "Venstre Back",
        "4": "Stopper",
        "5": "Stopper",
        "6": "Defensiv Midt",
        "7": "Højre Kant",
        "8": "Central Midt",
        "9": "Angriber",
        "10": "Offensiv Midt",
        "11": "Venstre Kant"
    }
    
    # Backup ordbog baseret på ROLECODE3
    role_dict = {
        "GKP": "Målmand",
        "DEF": "Forsvarsspiller",
        "MID": "Midtbane",
        "FWD": "Angriber"
    }

    # LOGIK:
    # Først tjekker vi POS-tallet
    if pos_raw in pos_dict:
        return pos_dict[pos_raw]
    
    # Hvis POS ikke er et tal (eller et ukendt tal), tjekker vi ROLECODE3
    if role_val in role_dict:
        return role_dict[role_val]
    
    # Hvis der står klar tekst i POS i forvejen
    if len(pos_raw) > 3 and pos_raw.lower() not in ["nan", "none"]:
        return pos_raw
    
    return "Ukendt"

# --- 2. PROFIL OG BILLEDER ---
def vis_spiller_billede(pid, w=110):
    pid_clean = str(pid).split('.')[0].replace('"', '').replace("'", "").strip()
    url = f"https://cdn5.wyscout.com/photos/players/public/g-{pid_clean}_100x130.png"
    std = "https://cdn5.wyscout.com/photos/players/public/ndplayer_100x130.png"
    try:
        resp = requests.head(url, timeout=0.8)
        st.image(url if resp.status_code == 200 else std, width=w)
    except:
        st.image(std, width=w)

# ... (vis_metrikker, vis_bokse_lodret, vis_profil uændret fra tidligere, 
# men de vil nu modtage den korrekte 'POSITION' tekst)

# --- 3. HOVEDFUNKTION ---
def vis_side():
    if "main_data" not in st.session_state:
        st.error("Data ikke fundet.")
        return
    
    all_data = st.session_state["main_data"]
    stats_df = all_data[4]
    df = all_data[5].copy()

    # Find kolonner dynamisk
    c_id = find_col(df, 'id')
    c_dato = find_col(df, 'dato')
    c_navn = find_col(df, 'navn')
    c_klub = find_col(df, 'klub')
    c_rating = find_col(df, 'rating_avg')
    c_status = find_col(df, 'status')
    c_scout = find_col(df, 'scout')

    # Konverteringer
    df['DATO_DT'] = pd.to_datetime(df[c_dato], errors='coerce')
    df[c_rating] = pd.to_numeric(df[c_rating].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    # BRUGER map_position til at lave den nye kolonne
    df['POS_PAEN'] = df.apply(map_position, axis=1)
    
    df = df.sort_values('DATO_DT')

    st.subheader("Scouting Database")
    
    # Filter-opsætning
    with st.popover("Filtrér", use_container_width=True):
        p_opts = sorted([str(x) for x in df['POS_PAEN'].unique() if str(x).strip() != ""])
        valgt_pos = st.multiselect("Position", options=p_opts, key="filter_pos")
        
        rating_range = st.slider("Rating", 0.0, 5.0, (0.0, 5.0), step=0.1, key="filter_rating")

    # Filtrering
    f_df = df.groupby(c_id).tail(1).copy()
    
    if valgt_pos:
        f_df = f_df[f_df['POS_PAEN'].isin(valgt_pos)]
    
    f_df = f_df[(f_df[c_rating] >= rating_range[0]) & (f_df[c_rating] <= rating_range[1])]

    # VISNING I TABEL
    vis_cols = [c_navn, 'POS_PAEN', c_klub, c_rating, c_status, c_dato, c_scout]
    
    st.dataframe(
        f_df[vis_cols],
        use_container_width=True, 
        hide_index=True, 
        column_config={
            "POS_PAEN": "Position",
            c_rating: st.column_config.NumberColumn("Rating", format="%.1f"),
            c_dato: st.column_config.DateColumn("Dato", format="DD/MM/YYYY")
        }
    )

if __name__ == "__main__":
    vis_side()
