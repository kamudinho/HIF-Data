import streamlit as st
import pandas as pd
from datetime import datetime

# Globale værdier
try:
    from data.utils.team_mapping import TOURNAMENTCALENDAR_NAME
except ImportError:
    TOURNAMENTCALENDAR_NAME = "2025/2026"

def map_position_detail(pos_code):
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back", 
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt", 
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber", 
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    clean_code = str(pos_code).split('.')[0].strip()
    if clean_code == "B": return "B-Liste / Ungdom"
    return pos_map.get(clean_code, clean_code if clean_code not in ["nan", "None", ""] else "Ukendt")

@st.cache_data(ttl=600)
def process_squad_data(df_spillere):
    """Denne kører kun én gang hvert 10. minut"""
    if df_spillere is None or df_spillere.empty:
        return pd.DataFrame()

    df = df_spillere.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Filtrér og rens lynhurtigt
    if 'SEASONNAME' in df.columns:
        df = df[df['SEASONNAME'] == TOURNAMENTCALENDAR_NAME]
    if 'PLAYER_WYID' in df.columns:
        df = df.drop_duplicates(subset=['PLAYER_WYID'])

    # Vektoriserede beregninger (langt hurtigere end .apply)
    idag = datetime.now()
    df['BIRTHDATE'] = pd.to_datetime(df['BIRTHDATE'], dayfirst=True, errors='coerce')
    df['CONTRACT'] = pd.to_datetime(df['CONTRACT'], dayfirst=True, errors='coerce')
    df['HEIGHT'] = pd.to_numeric(df['HEIGHT'], errors='coerce')
    
    df['ALDER'] = (idag - df['BIRTHDATE']).dt.days // 365
    df['POS_NAVN'] = df['POS'].apply(map_position_detail)
    
    sort_map = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
    df['sort_order'] = df['ROLECODE3'].map(sort_map).fillna(5)
    return df.sort_values(by=['sort_order', 'LASTNAME'])

def vis_side(df_raw):
    # 1. Hent færdigbehandlet data (sker øjeblikkeligt pga. cache)
    df_working = process_squad_data(df_raw)
    
    if df_working.empty:
        st.error("Ingen data fundet.")
        return

    # 2. Søgefunktion (kører lokalt på det cachede df)
    search = st.text_input("", placeholder="Søg spiller eller position...", label_visibility="collapsed")
    if search:
        mask = (df_working['POS_NAVN'].str.contains(search, case=False, na=False) | 
                df_working['NAVN'].str.contains(search, case=False, na=False))
        df_display = df_working[mask]
    else:
        df_display = df_working

    # 3. HTML Tabel med list-comprehension (hurtigere end for-loop)
    idag = datetime.now()
    
    rows = []
    for _, r in df_display.iterrows():
        c_bg = "transparent"
        if pd.notna(r['CONTRACT']):
            d = (r['CONTRACT'] - idag).days
            if d < 183: c_bg = "#ffcccc"
            elif d <= 365: c_bg = "#ffffcc"
        
        f_dag = r['BIRTHDATE'].strftime('%d.%m.%Y') if pd.notna(r['BIRTHDATE']) else "-"
        k_dag = r['CONTRACT'].strftime('%d.%m.%Y') if pd.notna(r['CONTRACT']) else "-"
        hojde = f"{int(r['HEIGHT'])} cm" if pd.notna(r['HEIGHT']) and r['HEIGHT'] > 0 else "-"
        
        rows.append(f"""
            <tr style="border-bottom:1px solid #f2f2f2;">
                <td style="padding:10px 15px; color:#666; font-size:12px;">{r['POS_NAVN']}</td>
                <td style="padding:10px 15px; font-weight:600; color:#222;">{r['NAVN']}</td>
                <td style="padding:10px 15px; text-align:center; color:#444;">{f_dag}</td>
                <td style="padding:10px 15px; text-align:center; color:#444;">{hojde}</td>
                <td style="padding:10px 15px; text-align:center; color:#444;">{r['FOD'] if pd.notna(r['FOD']) else '-'}</td>
                <td style="padding:10px 15px; text-align:right; font-weight:500; background-color:{c_bg};">{k_dag}</td>
            </tr>""")

    # Saml det hele til én stor tabel-streng
    html_output = f"""
    <div style="background:white; border:1px solid #eee; border-radius:4px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
        <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:14px;">
            <tr style="background:#fafafa; border-bottom: 2px solid #cc0000; color:#888; font-size:11px; text-transform:uppercase;">
                <th style="padding:12px 15px; text-align:left;">Position</th>
                <th style="padding:12px 15px; text-align:left;">Spiller</th>
                <th style="padding:12px 15px; text-align:center;">Født</th>
                <th style="padding:12px 15px; text-align:center;">Højde</th>
                <th style="padding:12px 15px; text-align:center;">Fod</th>
                <th style="padding:12px 15px; text-align:right;">Kontrakt</th>
            </tr>
            {rows}  </table>
    </div>
    """
    
    # DETTE ER DEN VIGTIGE LINJE:
    html_output = html_start + rows + "</table></div>"
    
    # BRUG DENNE LINJE - og vær sikker på den ikke er indrykket for meget
    st.markdown(html_output, unsafe_allow_html=True)

    # 4. Metrics
    st.write("")
    m1, m2, m3 = st.columns(3)
    m1.metric("Trupstørrelse", len(df_display))
    h_avg = df_display[df_display['HEIGHT'] > 0]['HEIGHT'].mean()
    m2.metric("Gns. Højde", f"{h_avg:.1f} cm" if pd.notna(h_avg) else "-")
    m3.metric("Gns. Alder", f"{df_display['ALDER'].mean():.1f} år" if not df_display['ALDER'].empty else "-")
