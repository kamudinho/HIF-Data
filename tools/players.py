import streamlit as st
import pandas as pd
from datetime import datetime

# Prøv at hente sæsonnavn
try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "2025/2026"

def map_position_detail(pos_code):
    clean_code = str(pos_code).split('.')[0].strip()
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back", 
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt", 
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber", 
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    if clean_code == "B": return "B-Liste / Ungdom"
    return pos_map.get(clean_code, clean_code if clean_code not in ["nan", "None", ""] else "Ukendt")

def vis_side(df_spillere):
    if df_spillere is None or df_spillere.empty:
        st.error("Kunne ikke finde spillerdata.")
        return

    # 1. CSS
    st.markdown("""
        <style>
            [data-testid="column"] {
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            }
            div[data-testid="stHorizontalBlock"] > div:last-child div[data-testid="stVerticalBlock"] {
                align-items: flex-end !important;
            }
            div[data-testid="stSegmentedControl"] {
                width: fit-content !important;
                margin-left: auto !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # 2. BRANDING
    st.markdown(f"""<div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">TRUPOVERSIGT</h3>
    </div>""", unsafe_allow_html=True)

    # 3. DATA
    df_working = df_spillere.copy()
    idag = datetime.now()
    df_working['BIRTHDATE'] = pd.to_datetime(df_working['BIRTHDATE'], dayfirst=True, errors='coerce')
    df_working['CONTRACT'] = pd.to_datetime(df_working['CONTRACT'], dayfirst=True, errors='coerce')
    df_working['HEIGHT'] = pd.to_numeric(df_working['HEIGHT'], errors='coerce')
    df_working['ALDER'] = df_working['BIRTHDATE'].apply(lambda x: idag.year - x.year - ((idag.month, idag.day) < (x.month, x.day)) if pd.notna(x) else None)
    df_working['POS_NAVN'] = df_working['POS'].apply(map_position_detail)
    sort_map = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
    df_working['sort_order'] = df_working['ROLECODE3'].map(sort_map).fillna(5)
    df_working = df_working.sort_values(by=['sort_order', 'LASTNAME'])

    # 4. SØG
    search = st.text_input("", placeholder="Søg...", label_visibility="collapsed")
    if search:
        mask = (df_working['POS_NAVN'].str.contains(search, case=False, na=False) | df_working['NAVN'].str.contains(search, case=False, na=False))
        df_working = df_working[mask]

    # 5. BYG TABEL (Vigtigt: Ingen indrykning i de rå strenge)
    html_start = """<div style="background:white; border:1px solid #eee; border-radius:4px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
    <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:14px;">
    <tr style="background:#fafafa; border-bottom: 2px solid #df003b; color:#888; font-size:11px; text-transform:uppercase;">
    <th style="padding:12px 15px; text-align:left;">Position</th>
    <th style="padding:12px 15px; text-align:left;">Spiller</th>
    <th style="padding:12px 15px; text-align:center;">Født</th>
    <th style="padding:12px 15px; text-align:center;">Højde</th>
    <th style="padding:12px 15px; text-align:center;">Fod</th>
    <th style="padding:12px 15px; text-align:right;">Kontrakt</th></tr>"""
    
    rows = ""
    for _, r in df_working.iterrows():
        c_bg = "transparent"
        if pd.notna(r['CONTRACT']):
            d = (r['CONTRACT'] - idag).days
            if d < 183: c_bg = "#ffcccc"
            elif d <= 365: c_bg = "#ffffcc"
        
        f_dag = r['BIRTHDATE'].strftime('%d.%m.%Y') if pd.notna(r['BIRTHDATE']) else "-"
        k_dag = r['CONTRACT'].strftime('%d.%m.%Y') if pd.notna(r['CONTRACT']) else "-"
        hojde = f"{int(r['HEIGHT'])} cm" if pd.notna(r['HEIGHT']) and r['HEIGHT'] > 0 else "-"
        
        rows += f"""<tr style="border-bottom:1px solid #f2f2f2;">
        <td style="padding:10px 15px; color:#666; font-size:12px;">{r['POS_NAVN']}</td>
        <td style="padding:10px 15px; font-weight:600; color:#222;">{r['NAVN']}</td>
        <td style="padding:10px 15px; text-align:center; color:#444;">{f_dag}</td>
        <td style="padding:10px 15px; text-align:center; color:#444;">{hojde}</td>
        <td style="padding:10px 15px; text-align:center; color:#444;">{r['FOD'] if pd.notna(r['FOD']) else '-'}</td>
        <td style="padding:10px 15px; text-align:right; font-weight:500; background-color:{c_bg};">{k_dag}</td></tr>"""

    full_html = html_start + rows + "</table></div>"
    
    # Render nu
    st.markdown(full_html, unsafe_allow_html=True)

    # 6. STATS
    st.write("")
    c1, c2, c3 = st.columns(3)
    c1.metric("Antal Spillere", len(df_working))
    h_avg = df_working[df_working['HEIGHT'] > 0]['HEIGHT'].mean()
    c2.metric("Gns. Højde", f"{h_avg:.1f} cm" if pd.notna(h_avg) else "-")
    c3.metric("Gns. Alder", f"{df_working['ALDER'].mean():.1f} år" if not df_working['ALDER'].empty else "-")
