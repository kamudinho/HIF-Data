import streamlit as st
import pandas as pd

def vis_side(df_raw=None):
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet.")
        return
        
    dp = st.session_state["dp"]
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logo_map = dp.get("logo_map", {})

    # DEBUG INFO I SIDEBAR
    st.sidebar.write("### Debug Info")
    st.sidebar.write(f"Antal rækker i df_matches: {len(df_matches)}")
    if not df_matches.empty:
        st.sidebar.write("Sæsoner fundet:", df_matches['TOURNAMENTCALENDAR_NAME'].unique())

    if df_matches.empty:
        st.warning(f"Ingen kampdata fundet for Opta ID: {dp.get('OP_UUID')}")
        st.info("Tjek om TOURNAMENTCALENDAR_NAME matcher '2025/2026' i Snowflake.")
        return

    # Resten af din kode fortsætter her...
    df_matches.columns = [c.upper() for c in df_matches.columns]

    st.markdown(f"## 🗓️ Kampprogram & Resultater")

    # --- 2. FILTRERING ---
    # I stedet for kun UUID, filtrerer vi på NAVN for at være sikker, 
    # da Opta UUID'er kan variere mellem miljøer.
    show_hif_only = st.toggle("Vis kun Hvidovre IF kampe", value=True)
    
    if show_hif_only:
        # Vi leder efter "Hvidovre" i enten hjemme- eller udeholdets navn
        mask = (df_matches["CONTESTANTHOME_NAME"].str.contains("Hvidovre", case=False, na=False)) | \
               (df_matches["CONTESTANTAWAY_NAME"].str.contains("Hvidovre", case=False, na=False))
        display_df = df_matches[mask].copy()
    else:
        display_df = df_matches.copy()

    if display_df.empty:
        st.info("Ingen kampe matchede filtreringen.")
        return

    # --- 3. VISNING PER RUNDE ---
    # Sørg for at MATCHDAY er tal
    display_df["MATCHDAY"] = pd.to_numeric(display_df["MATCHDAY"], errors='coerce').fillna(0)
    rounds = sorted(display_df["MATCHDAY"].unique(), reverse=True) # Nyeste runder øverst
    
    for r in rounds:
        with st.expander(f"Runde {int(r)}", expanded=(r == max(rounds))):
            round_matches = display_df[display_df["MATCHDAY"] == r]
            
            for _, match in round_matches.iterrows():
                h_name = match.get("CONTESTANTHOME_NAME", "Ukendt")
                a_name = match.get("CONTESTANTAWAY_NAME", "Ukendt")
                h_score = match.get("TOTAL_HOME_SCORE", 0)
                a_score = match.get("TOTAL_AWAY_SCORE", 0)
                status = match.get("STATUS", "")
                
                # Container til hver kamp
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([1, 4, 2, 4, 1])
                    
                    # Hjemmehold
                    with col1:
                        st.image(logo_map.get(h_name, "https://via.placeholder.com/50"), width=30)
                    with col2:
                        st.markdown(f"**{h_name}**" if "Hvidovre" in h_name else h_name)
                    
                    # Resultat / vs
                    with col3:
                        if status.lower() in ["played", "closed", "fulltime"]:
                            st.markdown(f"<h4 style='text-align: center; margin: 0;'>{int(h_score)} - {int(a_score)}</h4>", unsafe_allow_html=True)
                        else:
                            st.markdown("<p style='text-align: center; margin: 0; color: gray;'>vs</p>", unsafe_allow_html=True)
                    
                    # Udehold
                    with col4:
                        st.markdown(f"<div style='text-align: right;'>**{a_name}**</div>" if "Hvidovre" in a_name else f"<div style='text-align: right;'>{a_name}</div>", unsafe_allow_html=True)
                    with col5:
                        st.image(logo_map.get(a_name, "https://via.placeholder.com/50"), width=30)
                    
                    st.divider()

    # Sidebar debug
    if st.sidebar.checkbox("Vis rå Opta data"):
        st.dataframe(df_matches)
