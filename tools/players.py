import streamlit as st
import pandas as pd
from datetime import datetime

def map_position_detail(pos_code):
    """Oversætter de numeriske koder (1-11) fra POS-kolonnen til detaljeret dansk tekst."""
    clean_code = str(pos_code).split('.')[0].strip()
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back", "4": "Midtstopper",
        "5": "Midtstopper", "6": "Defensiv Midt", "7": "Højre Kant", "8": "Central Midt",
        "9": "Angriber", "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    return pos_map.get(clean_code, clean_code if clean_code not in ["nan", "None", ""] else "Ukendt")

def vis_side(df_spillere):
    if df_spillere is None or df_spillere.empty:
        st.error("Kunne ikke finde spillerdata.")
        return

    # --- 1. CSS FOR ENSRETNING ---
    st.markdown("""
        <style>
            .block-container { padding-top: 1rem !important; }
            /* Gør søgefeltet lidt mere diskret */
            .stTextInput > div > div > input { background-color: #fafafa; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA-PROCESSERING ---
    df_working = df_spillere.copy()
    idag = datetime.now()
    
    df_working['BIRTHDATE'] = pd.to_datetime(df_working['BIRTHDATE'], dayfirst=True, errors='coerce')
    df_working['CONTRACT'] = pd.to_datetime(df_working['CONTRACT'], dayfirst=True, errors='coerce')
    df_working['ALDER'] = df_working['BIRTHDATE'].apply(
        lambda x: idag.year - x.year - ((idag.month, idag.day) < (x.month, x.day)) if pd.notna(x) else None
    )
    df_working['POS_NAVN'] = df_working['POS'].apply(map_position_detail)

    # Sortering
    sort_map = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
    df_working['sort_order'] = df_working['ROLECODE3'].map(sort_map).fillna(5)
    df_working = df_working.sort_values(by=['sort_order', 'LASTNAME'])

    # --- 3. SØGEFUNKTION ---
    search = st.text_input("Søg i truppen...", "", placeholder="Søg på navn eller position")
    if search:
        mask = (df_working['POS_NAVN'].str.contains(search, case=False, na=False) |
                df_working['NAVN'].str.contains(search, case=False, na=False))
        df_working = df_working[mask]

    # --- 4. RENDER HTML TABEL (Top 5 Stil) ---
    html = """
    <div style="background:white; border:1px solid #eee; border-radius:4px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
        <table style="width:100%; border-collapse:collapse; font-family:sans-serif; font-size:14px;">
            <tr style="background:#fafafa; border-bottom: 2px solid #df003b; color:#888; font-size:11px; text-transform:uppercase;">
                <th style="padding:12px 15px; text-align:left;">Position</th>
                <th style="padding:12px 15px; text-align:left;">Spiller</th>
                <th style="padding:12px 15px; text-align:center;">Født</th>
                <th style="padding:12px 15px; text-align:center;">Højde</th>
                <th style="padding:12px 15px; text-align:center;">Fod</th>
                <th style="padding:12px 15px; text-align:right;">Kontrakt</th>
            </tr>
    """

    for _, r in df_working.iterrows():
        # Kontraktfarve logik
        contr_color = "inherit"
        contr_bg = "transparent"
        if pd.notna(r['CONTRACT']):
            dage_til_udloeb = (r['CONTRACT'] - idag).days
            if dage_til_udloeb < 183: # Under et halvt år
                contr_bg = "#ffcccc"
            elif dage_til_udloeb <= 365: # Under et år
                contr_bg = "#ffffcc"

        fod = r['FOD'] if pd.notna(r['FOD']) else "-"
        hojde = f"{int(r['HEIGHT'])} cm" if pd.notna(r['HEIGHT']) and r['HEIGHT'] > 0 else "-"
        født = r['BIRTHDATE'].strftime('%d.%m.%Y') if pd.notna(r['BIRTHDATE']) else "-"
        kontrakt = r['CONTRACT'].strftime('%d.%m.%Y') if pd.notna(r['CONTRACT']) else "-"

        html += f"""
            <tr style="border-bottom:1px solid #f2f2f2;">
                <td style="padding:10px 15px; color:#666; font-size:12px;">{r['POS_NAVN']}</td>
                <td style="padding:10px 15px; font-weight:600; color:#222;">{r['NAVN']}</td>
                <td style="padding:10px 15px; text-align:center; color:#444;">{født}</td>
                <td style="padding:10px 15px; text-align:center; color:#444;">{hojde}</td>
                <td style="padding:10px 15px; text-align:center; color:#444;">{fod}</td>
                <td style="padding:10px 15px; text-align:right; font-weight:500; background-color:{contr_bg};">{kontrakt}</td>
            </tr>
        """

    html += "</table></div>"
    st.write(html, unsafe_allow_html=True)

    # --- 5. STATISTIK I BUNDEN ---
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Antal Spillere", len(df_working))
    with c2:
        h_avg = df_working[df_working['HEIGHT'] > 0]['HEIGHT'].mean()
        st.metric("Gns. Højde", f"{h_avg:.1f} cm" if pd.notna(h_avg) else "-")
    with c3:
        age_avg = df_working['ALDER'].mean()
        st.metric("Gns. Alder", f"{age_avg:.1f} år" if pd.notna(age_avg) else "-")
