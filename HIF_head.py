import streamlit as st
import pandas as pd
import data.hif_load as hif_load

def vis_side():
    # Brand-farve fra din app
    HIF_ROD = "#df003b"
    
    st.markdown(f'<div style="font-size: 24px; font-weight: 700; color: #1a1a1a; margin-bottom: 20px;">Hvidovre IF - Hovedoversigt (2025/2026)</div>', unsafe_allow_html=True)
    
    # 1. Hent data via hif_load (eller brug cachede elementer hvis tilgængelig)
    try:
        # Hent f.eks. truppen eller holddata
        dp_quick = hif_load.get_squad_only()
        antal_spillere = len(dp_quick.get("players", [])) if dp_quick and "players" in dp_quick else 0
    except Exception:
        antal_spillere = 0

    # 2. Overordnede Metrikker / KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Sæson", value="2025/2026")
    with col2:
        st.metric(label="Team ID (Wyscout)", value="7490")
    with col3:
        st.metric(label="Aktive Spillere i Truppen", value=str(antal_spillere))
    with col4:
        st.metric(label="Liga", value="NordicBet Liga")

    st.divider()

    # 3. Sektion med genveje eller status
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📊 Velkommen til HIF Data Hub")
        st.write("""
            Her har du det samlede overblik over Hvidovre IF's data, modstanderanalyser, 
            spillerstatistikker og scouting-emner for **2025/2026**-sæsonen.
        """)
        
        # Eksempel på at vise lidt data fra tabeller hvis muligt
        st.info("💡 **Tip:** Brug menuen i venstre side til at navigere mellem Holdanalyse, Spilleranalyse og Scouting.")

    with col_right:
        st.subheader("⚡ Hurtige Handlinger")
        if st.button("Ryd App Cache", use_container_width=True):
            st.cache_data.clear()
            st.success("Cachen blev rydet!")
            st.rerun()
            
        st.markdown(f"""
            <div style="background-color: #f9f9f9; padding: 15px; border-radius: 6px; border-left: 4px solid {HIF_ROD}; margin-top: 15px;">
                <b>System Status</b><br>
                Forbindelse til datakilder: Aktiv<br>
                Kompetence: NordicBet Liga (328)
            </div>
        """, unsafe_allow_html=True)
