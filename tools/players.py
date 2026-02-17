import streamlit as st
import pandas as pd
from datetime import datetime

# Prøv at hente sæsonnavn fra din data-mappe
try:
    from data.season_show import SEASONNAME
except ImportError:
    SEASONNAME = "2025/2026"

def map_position_detail(pos_code):
    """Oversætter de numeriske koder (1-11) fra POS-kolonnen til dansk tekst."""
    clean_code = str(pos_code).split('.')[0].strip()
    pos_map = {
        "1": "Målmand", "2": "Højre Back", "3": "Venstre Back", 
        "4": "Midtstopper", "5": "Midtstopper", "6": "Defensiv Midt", 
        "7": "Højre Kant", "8": "Central Midt", "9": "Angriber", 
        "10": "Offensiv Midt", "11": "Venstre Kant"
    }
    if clean_code == "B":
        return "B-Liste / Ungdom"
    return pos_map.get(clean_code, clean_code if clean_code not in ["nan", "None", ""] else "Ukendt")

def vis_side(df_spillere):
    if df_spillere is None or df_spillere.empty:
        st.error("Kunne ikke finde spillerdata (players.csv).")
        return

    # --- 1. CSS INJECTION (Layout-synkronisering med Top 5) ---
    st.markdown("""
        <style>
            /* Fjern Streamlits standard top-padding for at flugte med Top 5 */
            .block-container { 
                padding-top: 1rem !important; 
                max-width: 98% !important; 
            }
            
            /* Gør søgefeltet kompakt og diskret */
            .stTextInput > div > div > input { 
                background-color: #fafafa; 
                border-radius: 4px;
                border: 1px solid #eee;
            }

            /* Container til den nye tabel */
            .tabel-wrapper { 
                margin-top: 5px;
                background: white; 
                border: 1px solid #eee; 
                border-radius: 4px; 
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. KOMPAKT TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem; text-transform:uppercase;">TRUPOVERSIGT</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # --- 3. DATA-PROCESSERING ---
    df_working = df_spillere.copy()
    idag = datetime.now()
    
    df_working['BIRTHDATE'] = pd.to_datetime(df_working['BIRTHDATE'], dayfirst=True, errors='coerce')
    df_working['CONTRACT'] = pd.to_datetime(df_working['CONTRACT'], dayfirst=True, errors='coerce')
    df_working['HEIGHT'] = pd.to_numeric(df_working['HEIGHT'], errors='coerce')

    # Beregn Alder
    df_working['ALDER'] = df_working['BIRTHDATE'].apply(
        lambda x: idag.year - x.year - ((idag.month, idag.day) < (x.month, x.day)) if pd.notna(x) else None
    )

    # Positioner og sortering (MM -> FOR -> MID -> ANG)
    df_working['POS_NAVN'] = df_working['POS'].apply(map_position_detail)
    sort_map = {"GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
    df_working['sort_order'] = df_working['ROLECODE3'].map(sort_map).fillna(5)
    df_working = df_working.sort_values(by=['sort_order', 'LASTNAME'])

    # --- 4. SØGEFUNKTION ---
    search = st.text_input("", placeholder="Søg efter spiller eller position...", label_visibility="collapsed")
    if search:
        mask = (
            df_working['POS_NAVN'].str.contains(search, case=False, na=False) |
            df_working['NAVN'].str.contains(search, case=False, na=False)
        )
        df_working = df_working[mask]

    # --- 5. BYG HTML TABEL ---
    html = """
    <div class="tabel-wrapper">
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
        # Kontrakt farve-logik
        contr_bg = "transparent"
        if pd.notna(r['CONTRACT']):
            dage = (r['CONTRACT'] - idag).days
            if dage < 183:
                contr_bg = "#ffcccc" # Rød (under 6 mdr)
            elif dage <= 365:
                contr_bg = "#ffffcc" # Gul (under 1 år)

        fod = r['FOD'] if pd.notna(r['FOD']) else "-"
        hojde = f"{int(r['HEIGHT'])} cm" if pd.notna(r['HEIGHT']) and r['HEIGHT'] > 0 else "-"
        fodselsdag = r['BIRTHDATE'].strftime('%d.%m.%Y') if pd.notna(r['BIRTHDATE']) else "-"
        kontrakt = r['CONTRACT'].strftime('%d.%m.%Y') if pd.notna(r['CONTRACT']) else "-"

        html += f"""
            <tr style="border-bottom:1px solid #f2f2f2;">
                <td style="padding:10px 15px; color:#666; font-size:12px;">{r['POS_NAVN']}</td>
                <td style="padding:10px 15px; font-weight:600; color:#222;">{r['NAVN']}</td>
                <td style="padding:10px 15px; text-align:center; color:#444;">{fodselsdag}</td>
                <td style="padding:10px 15px; text-align:center; color:#444;">{hojde}</td>
                <td style="padding:10px 15px; text-align:center; color:#444;">{fod}</td>
                <td style="padding:10px 15px; text-align:right; font-weight:500; background-color:{contr_bg};">{kontrakt}</td>
            </tr>
        """

    html += "</table></div>"
    
    # RENDER TABELLEN SOM HTML
    st.markdown(html, unsafe_allow_html=True)

    # --- 6. STATISTIK I BUNDEN ---
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Antal Spillere", len(df_working))
    with c2:
        valid_h = df_working[df_working['HEIGHT'] > 0]['HEIGHT']
        st.metric("Gns. Højde", f"{valid_h.mean():.1f} cm" if not valid_h.empty else "-")
    with c3:
        st.metric("Gns. Alder", f"{df_working['ALDER'].mean():.1f} år" if not df_working['ALDER'].empty else "-")
