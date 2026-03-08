import streamlit as st
import pandas as pd

def vis_side(dp):
    # --- 1. DATAGRUNDLAG ---
    df_matches = dp.get("opta", {}).get("matches", pd.DataFrame()).copy()
    df_stats = dp.get("opta", {}).get("team_stats", pd.DataFrame()).copy()

    # Rens og standardiser
    if not df_matches.empty:
        df_matches.columns = [c.upper() for c in df_matches.columns]
        # Vi lader UUID'erne være som de er i første omgang for at undgå mismatch
        for col in ['CONTESTANTHOME_OPTAUUID', 'CONTESTANTAWAY_OPTAUUID', 'MATCH_OPTAUUID']:
            if col in df_matches.columns:
                df_matches[col] = df_matches[col].astype(str).str.strip()

    # --- 2. HOLDVALG & UUID ---
    config = dp.get("config", {})
    valgt_liga_global = config.get("liga_navn", "1. Division")
    
    # Hent holdlisten fra din mapping-fil
    from data.utils.team_mapping import TEAMS
    liga_hold_options = {n: i.get("opta_uuid") for n, i in TEAMS.items() if i.get("league") == valgt_liga_global}
    h_list = sorted(liga_hold_options.keys())

    # Vælg Hvidovre som standard
    hif_idx = h_list.index("Hvidovre") if "Hvidovre" in h_list else 0
    valgt_navn = st.selectbox("Vælg hold", h_list, index=hif_idx)
    
    # VIGTIGT: Vi henter UUID'en og tjekker begge cases (store/små)
    v_uuid = str(liga_hold_options[valgt_navn]).strip()

    # --- 3. FILTRERING (Her det ofte går galt) ---
    # Vi tjekker om v_uuid findes i enten hjemme- eller ubehold-kolonnen
    team_matches = df_matches[
        (df_matches['CONTESTANTHOME_OPTAUUID'].str.contains(v_uuid, case=False, na=False)) | 
        (df_matches['CONTESTANTAWAY_OPTAUUID'].str.contains(v_uuid, case=False, na=False))
    ].copy()

    # --- FEJL-TRACKER ---
    if team_matches.empty:
        st.error(f"Kunne ikke finde kampe for {valgt_navn} (ID: {v_uuid})")
        if not df_matches.empty:
            st.write("Tilgængelige ID'er i data (første 5 rækker):")
            st.write(df_matches[['CONTESTANTHOME_NAME', 'CONTESTANTHOME_OPTAUUID']].head())
        return

    # --- 4. SEKTIONERING AF KAMPE ---
    # Vi er mere fleksible med status-tjekket
    played = team_matches[team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]
    future = team_matches[~team_matches['MATCH_STATUS'].str.lower().str.contains('play|full|finish', na=False)]

    # (Resten af din tegn_kampe logik her...)
    st.success(f"Fandt {len(played)} spillede kampe og {len(future)} kommende kampe.")
    
    t1, t2 = st.tabs(["⚽ RESULTATER", "📅 PROGRAM"])
    with t1:
        # Kald din tegn_kampe her
        st.write(played) # Midlertidig for at se om data er der
    with t2:
        st.write(future)
