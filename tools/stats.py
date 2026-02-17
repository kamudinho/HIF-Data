import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# --- 0. CSS TIL TOTAL KANT-TIL-KANT FLEX ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
            max-width: 98% !important;
        }
        
        /* Skaber en container der skyder indholdet til hver sin side */
        .custom-ui-container {
            display: flex;
            justify-content:间-between;
            align-items: center;
            width: 100%;
            margin-bottom: 10px;
        }

        /* Tvinger Streamlits widgets til at fylde det de skal uden ekstra margin */
        div[data-testid="stHorizontalBlock"] {
            gap: 0px !important;
        }
        
        /* Tvinger segmented control helt til højre kant */
        div[data-testid="stSegmentedControl"] {
            margin-left: auto !important;
            width: fit-content !important;
        }
    </style>
""", unsafe_allow_html=True)

def vis_side(spillere, player_stats_sn):
    # (Sektion 1 & 2 er identiske med dit tidligere script...)
    # --- 1. BRANDING ---
    st.markdown(f"""
        <div style="background-color:#df003b; padding:10px; border-radius:4px; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; letter-spacing:1px; font-size:1.1rem;">SPILLERSTATISTIK</h3>
            <p style="color:white; margin:0; text-align:center; font-size:12px; opacity:0.8;">Hvidovre IF | {SEASONNAME}</p>
        </div>
    """, unsafe_allow_html=True)

    # ... (Data klargøring her) ...

    # --- 3. UI KONTROLLER (RETTET TIL KANT-TIL-KANT) ---
    # Vi bruger én række, men to separate div-containere via columns med gap="0"
    c1, c2 = st.columns([1, 1], gap="small")
    
    with c1:
        # Venstre-stillet
        valg_label = st.pills("Statistik", tilgaengelige, default="Mål", label_visibility="collapsed")
    
    with c2:
        # Højre-stillet via CSS 'margin-left: auto'
        visning = st.segmented_control("Visning", ["Total", "Pr. 90"], default="Total", label_visibility="collapsed")

    # --- 4. BEREGNING & 5. GRAF (Som før) ---
    # ... restfamilien af koden ...
