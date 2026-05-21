import streamlit as st
import pandas as pd

def vis_side():
    # --- 1. VELKOMST & HURTIG STATUS ---
    col_header, col_logo = st.columns([4, 1])
    with col_header:
        st.subheader("Hvidovre IF - Performance Dashboard")
        st.write("Velkommen tilbage. Her er de vigtigste opdateringer for staben.")
    
    st.markdown("---")

    # --- 2. KOMMENDE KAMP & TRANSFERS (TOP RÆKKE) ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏟️ Næste Modstander")
        # Her vil vi senere trække data fra din modstander-analyse
        with st.container(border=True):
            st.markdown("**SønderjyskE** (H)")
            st.caption("NordicBet Liga  |  Søndag d. 24. Maj  |  Hvidovre Stadion")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Form", "V-U-T-V-V")
            m2.metric("xG (Snit)", "1.42")
            m3.metric("Tabelsæde", "2.")

    with col2:
        st.markdown("### 📝 Transfer Update")
        with st.container(border=True):
            # Eksempel på visning af emner eller aktive forhandlinger
            st.write("Seneste 3 emner i kikkerten:")
            st.caption("1. Mads Hansen (FCM) - Scouting 82%")
            st.caption("2. Elias Jelert (FCK) - Monitoreres")
            st.caption("3. Mikkel Jensen (BIF) - Forhandling")
            if st.button("Gå til Database", use_container_width=True):
                st.session_state["main_menu_selection"] = "SCOUTING"
                st.session_state["sub_menu_selection"] = "Database"
                st.rerun()

    # --- 3. FORM-OVERBLIK (MIDTER RÆKKE) ---
    st.markdown("### 📊 Form Check (Seneste 5 kampe)")
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        st.write("**Hvidovre IF**")
        # Visualisering af form (Cirkler eller små bokse)
        st.markdown("🟢 🟢 🟡 🔴 🟢")
        st.caption("Seneste: 2-1 Sejr mod Hobro")

    with f_col2:
        st.write("**Næste Modstander (SønderjyskE)**")
        st.markdown("🟢 🟢 🟢 🟡 🟢")
        st.caption("Seneste: 4-0 Sejr mod B93")

    # --- 4. TRUP-STATUS & HURTIGE LINKS (BUND) ---
    st.markdown("---")
    b1, b2, b3 = st.columns(3)
    
    with b1:
        st.markdown("#### 🏥 Skadesliste")
        st.error("Matti Olsen (Knæ) - Retur Juni")
        st.warning("Christian Jakobsen (Ankel) - Tvivlsom")

    with b2:
        st.markdown("#### 🟨 Karantænefare")
        st.write("Daniel Stenderup (1 point)")
        st.write("Magnus Fredslund (3 point)")

    with b3:
        st.markdown("#### ⚡ Quick Actions")
        if st.button("Lav Scoutrapport", use_container_width=True):
            st.session_state["main_menu_selection"] = "SCOUTING"
            st.session_state["sub_menu_selection"] = "Scoutrapport"
            st.rerun()
