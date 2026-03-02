import streamlit as st
import pandas as pd

def vis_side(df_raw=None):
    if "dp" not in st.session_state:
        st.error("Data pakken 'dp' ikke fundet.")
        return
        
    dp = st.session_state["dp"]
    df_matches = dp.get("opta_matches", pd.DataFrame())
    logo_map = dp.get("logo_map", {})

    if df_matches.empty:
        st.warning(f"Ingen kampdata fundet.")
        return

    # Tving kolonnenavne til UPPERCASE med det samme
    df_matches.columns = [c.upper() for c in df_matches.columns]

    st.markdown(f"## 🗓️ Kampprogram & Resultater")

    # --- 1. FILTRERING (Hvidovre-værdier fra din konfiguration) ---
    show_hif_only = st.toggle("Vis kun Hvidovre IF kampe", value=True)
    
    if show_hif_only:
        mask = (df_matches["CONTESTANTHOME_NAME"].str.contains("Hvidovre", case=False, na=False)) | \
               (df_matches["CONTESTANTAWAY_NAME"].str.contains("Hvidovre", case=False, na=False))
        display_df = df_matches[mask].copy()
    else:
        display_df = df_matches.copy()

    # --- 2. SORTERING (Efter dato i stedet for runder) ---
    if "MATCH_DATE_FULL" in display_df.columns:
        display_df["MATCH_DATE_FULL"] = pd.to_datetime(display_df["MATCH_DATE_FULL"])
        display_df = display_df.sort_values("MATCH_DATE_FULL", ascending=False)

    if display_df.empty:
        st.info("Ingen kampe matchede filtreringen.")
        return

    # --- 3. VISNING (Simpel liste uden gruppering) ---
    for _, match in display_df.iterrows():
        h_name = match.get("CONTESTANTHOME_NAME", "Ukendt")
        a_name = match.get("CONTESTANTAWAY_NAME", "Ukendt")
        h_score = match.get("TOTAL_HOME_SCORE", 0)
        a_score = match.get("TOTAL_AWAY_SCORE", 0)
        
        # Formater dato til noget læsbart
        m_date = match["MATCH_DATE_FULL"].strftime('%d. %b %Y') if "MATCH_DATE_FULL" in match else ""

        with st.container():
            # Dato-label øverst
            st.caption(f"📅 {m_date}")
            
            col1, col2, col3, col4, col5 = st.columns([1, 4, 2, 4, 1])
            
            with col1:
                st.image(logo_map.get(h_name, "https://via.placeholder.com/50"), width=30)
            with col2:
                st.markdown(f"**{h_name}**" if "Hvidovre" in h_name else h_name)
            
            with col3:
                # Vi viser scoren uanset hvad, så længe vi tester
                st.markdown(f"<h4 style='text-align: center; margin: 0;'>{int(h_score)} - {int(a_score)}</h4>", unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"<div style='text-align: right;'>**{a_name}**</div>" if "Hvidovre" in a_name else f"<div style='text-align: right;'>{a_name}</div>", unsafe_allow_html=True)
            with col5:
                st.image(logo_map.get(a_name, "https://via.placeholder.com/50"), width=30)
            
            st.divider()

    # Sidebar debug - så vi kan se hvad der foregår bag kulissen
    if st.sidebar.checkbox("Vis rå tabel"):
        st.dataframe(df_matches)
