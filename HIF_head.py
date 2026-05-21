import streamlit as st
import pandas as pd
import os

def vis_side():
    # CSS til at styre generelle skriftstørrelser på forsiden
    st.markdown("""
        <style>
            .small-font { font-size: 12px !important; }
            .medium-font { font-size: 14px !important; }
            .transfer-item { font-size: 13px; margin-bottom: -5px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. DATALOAD ---
    # Transfers i 1. Division
    try:
        df_transfers = pd.read_csv("data/players/1div_overskrivning.csv")
        seneste_transfers = df_transfers.tail(5).iloc[::-1] 
    except:
        seneste_transfers = pd.DataFrame()

    # Egne scouting-emner (Emneliste)
    try:
        df_emner = pd.read_csv("data/scouting/emneliste.csv") 
        # SIKRING: Gør kolonnenavne store så de matcher din stil fra transfers-filen
        df_emner.columns = [c.upper() for c in df_emner.columns]
        seneste_emner = df_emner.tail(5).iloc[::-1]
    except Exception as e:
        # st.error(f"Fejl ved indlæsning af emner: {e}") # Fjern udkommentering for at debugge
        seneste_emner = pd.DataFrame()


    # --- 3. TOP SEKTION ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption("##### Næste Modstander")
        with st.container(border=True):
            st.markdown("### SønderjyskE (H)") # Større overskrift
            st.caption("NordicBet Liga  |  Søndag d. 24. Maj")
            
            m1, m2, m3 = st.columns(3)
            # Metrics har faste størrelser, men vi kan caption dem
            m1.metric("Form", "V-U-T")
            m2.metric("xG", "1.42")
            m3.metric("Plads", "2.")

    with col2:
        st.caption("##### Seneste Transfers (1. Div)")
        with st.container(border=True):
            if not seneste_transfers.empty:
                for _, row in seneste_transfers.iterrows():
                    # Bruger HTML for at styre præcis skriftstørrelse
                    st.markdown(f"<p class='transfer-item'><b>{row['KLUB']}</b>: {row['NAVN']}</p>", unsafe_allow_html=True)
            else:
                st.write("Ingen nye transfers.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Se alle transfers", use_container_width=True, key="btn_trans"):
                st.session_state["main_menu_selection"] = "SCOUTING"
                st.session_state["sub_menu_selection"] = "Database"
                st.rerun()

    with col3:
        st.caption("##### Nyeste på Emnelisten")
        with st.container(border=True):
            if not seneste_emner.empty:
                for _, row in seneste_emner.iterrows():
                    # Vi bruger de øverste kolonnenavne (NAVN, POSITION) som i transfer-filen
                    st.markdown(f"<p class='transfer-item'>⭐ <b>{row['NAVN']}</b> ({row['POSITION']})</p>", unsafe_allow_html=True)
            else:
                st.info("Emnelisten kunne ikke læses eller er tom.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Gå til Emnedatabase", use_container_width=True, key="btn_emne"):
                st.session_state["main_menu_selection"] = "SCOUTING"
                st.session_state["sub_menu_selection"] = "Emnedatabase"
                st.rerun()

    # --- 4. FORM-OVERBLIK ---
    st.markdown("##### Form Check")
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        with st.container(border=True):
            st.markdown("<p class='medium-font'><b>Hvidovre IF</b></p>", unsafe_allow_html=True)
            st.markdown("🟢 🟢 🟡 🔴 🟢")
            st.caption("Seneste: 2-1 mod Hobro")

    with f_col2:
        with st.container(border=True):
            st.markdown("<p class='medium-font'><b>SønderjyskE</b></p>", unsafe_allow_html=True)
            st.markdown("🟢 🟢 🟢 🟡 🟢")
            st.caption("Seneste: 4-0 mod B93")

    # --- 5. TRUP-STATUS & ACTIONS ---
    st.markdown("---")
    b1, b2, b3 = st.columns(3)
    
    with b1:
        st.markdown("<p class='medium-font'><b>Skadesliste</b></p>", unsafe_allow_html=True)
        st.error("Matti Olsen (Knæ)")
        st.warning("Christian Jakobsen (Tvivlsom)")

    with b2:
        st.markdown("<p class='medium-font'><b>Karantænefare</b></p>", unsafe_allow_html=True)
        st.write("Daniel Stenderup (1 point)")
        st.write("Magnus Fredslund (3 point)")

    with b3:
        st.markdown("<p class='medium-font'><b>⚡ Quick Actions</b></p>", unsafe_allow_html=True)
        if st.button("Ny Scoutrapport", use_container_width=True):
            st.session_state["main_menu_selection"] = "SCOUTING"
            st.session_state["sub_menu_selection"] = "Scoutrapport"
            st.rerun()
