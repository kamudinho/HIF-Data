import streamlit as st
import pandas as pd
import os

def vis_side():
    # --- 1. DATALOAD (Transfers) ---
    try:
        # Vi læser din specifikke sti
        df_transfers = pd.read_csv("data/players/1div_overskrivning.csv")
        # Sorter efter nyeste hvis TIMESTAMP findes, ellers tager vi de sidste i filen
        seneste_transfers = df_transfers.tail(5).iloc[::-1] 
    except:
        seneste_transfers = pd.DataFrame()

    # --- 2. VELKOMST & HURTIG STATUS ---
    st.write("Hvidovre IF - Performance Dashboard")
   
    st.markdown("---")

    # --- 3. KOMMENDE KAMP & TRANSFERS ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏟️ Næste Modstander")
        with st.container(border=True):
            st.markdown("**SønderjyskE** (H)")
            st.caption("NordicBet Liga  |  Søndag d. 24. Maj  |  Hvidovre Stadion")
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Form", "V-U-T-V-V")
            m2.metric("xG (Snit)", "1.42")
            m3.metric("Tabelsæde", "2.")

    with col2:
        st.caption("# 📝 Seneste Transfers (1. Div)")
        with st.container(border=True):
            if not seneste_transfers.empty:
                for _, row in seneste_transfers.iterrows():
                    # Viser Klub, Navn og Position fra din CSV
                    st.markdown(f"**{row['KLUB']}**: {row['NAVN']} ({row['POSITION']})")
            else:
                st.write("Ingen nye transfers registreret.")
            
            if st.button("Se alle transfers", use_container_width=True):
                st.session_state["main_menu_selection"] = "SCOUTING"
                st.session_state["sub_menu_selection"] = "Database"
                st.rerun()

    # --- 4. FORM-OVERBLIK ---
    st.markdown("### 📊 Form Check")
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        with st.container(border=True):
            st.write("**Hvidovre IF**")
            st.markdown("🟢 🟢 🟡 🔴 🟢")
            st.caption("Seneste: 2-1 mod Hobro")

    with f_col2:
        with st.container(border=True):
            st.write("**SønderjyskE**")
            st.markdown("🟢 🟢 🟢 🟡 🟢")
            st.caption("Seneste: 4-0 mod B93")

    # --- 5. TRUP-STATUS ---
    st.markdown("---")
    b1, b2, b3 = st.columns(3)
    
    with b1:
        st.markdown("#### 🏥 Skadesliste")
        st.error("Matti Olsen (Knæ)")
        st.warning("Christian Jakobsen (Tvivlsom)")

    with b2:
        st.markdown("#### 🟨 Karantænefare")
        st.write("Daniel Stenderup (1 point)")
        st.write("Magnus Fredslund (3 point)")

    with b3:
        st.markdown("#### ⚡ Quick Actions")
        if st.button("Ny Scoutrapport", use_container_width=True):
            st.session_state["main_menu_selection"] = "SCOUTING"
            st.session_state["sub_menu_selection"] = "Scoutrapport"
            st.rerun()
