import streamlit as st
import pandas as pd

def vis_side(dp=None):
    st.markdown("### Min Profil & Overblik")
    
    # Hent aktuel bruger fra session state
    bruger = st.session_state.get('user', 'ukendt')
    
    # Hent brugerinfo fra databasen hvis muligt
    try:
        from data.users import get_users
        user_db = get_users()
        user_info = user_db.get(bruger, {})
        rolle = user_info.get("role", "Ikke angivet")
    except Exception:
        rolle = "Scout / Medarbejder"

    # --- TOP KORT ---
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"Brugernavn: {bruger}")
    with col2:
        st.info(f"Rolle / Tilladelse: {rolle}")

    st.markdown("---")

    # --- OPGAVESOVERSIGT FOR BRUGEREN ---
    st.markdown("#### Dine Opgaver")
    
    try:
        import tools.admin_page.opgaver as opg
        df_opgaver = opg.indlaes_opgaver()
        
        if not df_opgaver.empty and "tildelt_til" in df_opgaver.columns:
            # Filtrer opgaver der tilhører den indloggede bruger (uafhængig af store/små bogstaver)
            mine_opgaver = df_opgaver[
                df_opgaver["tildelt_til"].astype(str).str.lower().str.strip() == bruger.lower().strip()
            ]
            
            if not mine_opgaver.empty:
                aktive = mine_opgaver[mine_opgaver["status"] != "Færdig"]
                faerdige = mine_opgaver[mine_opgaver["status"] == "Færdig"]
                
                # Metrikker
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Tildelt", len(mine_opgaver))
                m2.metric("Aktive / I gang", len(aktive))
                m3.metric("Færdigmeldte", len(faerdige))
                
                st.markdown("##### Aktive opgaver:")
                if not aktive.empty:
                    st.dataframe(aktive[["titel", "status", "beskrivelse"]], use_container_width=True)
                else:
                    st.success("Du har ingen udestående eller aktive opgaver lige nu.")
            else:
                st.info("Du har ikke fået tildelt nogen opgaver endnu.")
        else:
            st.info("Ingen opgaver fundet i systemet.")
            
    except Exception as e:
        st.warning(f"Kunne ikke indhente opgaver til profilen: {e}")

    st.markdown("---")
    
    # --- HURTIGE GENVEJE / HANDLINGER ---
    st.markdown("#### Personlige Indstillinger")
    st.write("Her kan der på sigt tilføjes mulighed for f.eks. at skifte adgangskode, vælge startside eller opdatere kontaktoplysninger.")
