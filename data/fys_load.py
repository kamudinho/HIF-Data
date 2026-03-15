import streamlit as st
import pandas as pd

def get_physical_package(dp):
    """
    Henter fysiske data fra datapakken (dp) og filtrerer til valgt kamp og Hvidovre.
    """
    # --- DEBUG SEKTION (Viser sig kun i appen) ---
    st.info("🔄 Starter indlæsning af fysisk pakke...")
    
    # 1. Forsøg at finde dataframe (df) i dp-pakken
    df = None
    
    # Vi tjekker først i dp['opta']['opta_physical_stats']
    if "opta" in dp and "opta_physical_stats" in dp["opta"]:
        df = dp["opta"]["opta_physical_stats"]
        st.success("✅ Fandt data i dp['opta']['opta_physical_stats']")
    
    # Hvis ikke fundet, tjekker vi i roden af dp
    elif "fysisk_data" in dp:
        df = dp["fysisk_data"]
        st.success("✅ Fandt data i dp['fysisk_data']")
        
    # 2. Hvis ingen data overhovedet er fundet
    if df is None:
        st.error("❌ Fejl: Kunne ikke finde fysiske data i datapakken (dp).")
        st.write("Tilgængelige nøgler i dp:", list(dp.keys()))
        return None

    # 3. Hvis dataframen er tom
    if df.empty:
        st.warning("⚠️ Tabellen med fysiske data er fundet, men den indeholder 0 rækker.")
        return None

    # --- DATABEHANDLING ---

    # Sikr os at vi har en kolonne til at vælge kampe
    if 'MATCH_DISPLAY' not in df.columns:
        # Hvis de originale navne findes fra din SQL join
        if 'CONTESTANTHOME_NAME' in df.columns and 'CONTESTANTAWAY_NAME' in df.columns:
            df['MATCH_DISPLAY'] = df['CONTESTANTHOME_NAME'] + " - " + df['CONTESTANTAWAY_NAME']
        else:
            # Fallback hvis kolonnenavne driller
            df['MATCH_DISPLAY'] = "Kamp ID: " + df['MATCH_SSIID'].astype(str)

    # Opret selectbox til valg af kamp
    kampe = sorted(df['MATCH_DISPLAY'].unique())
    valgt_kamp = st.selectbox("Vælg kamp for fysisk analyse", kampe)
    
    # Filtrer data til den valgte kamp
    match_df = df[df['MATCH_DISPLAY'] == valgt_kamp].copy()
    
    # Find Hvidovre IF
    # Vi bruger UUID'en fra dit dump: 56fa29c7-3a48-4186-9d14-dbf45fbc78d9
    # Men vi tjekker også på navnet for en sikkerheds skyld
    hif_uuid = "56fa29c7-3a48-4186-9d14-dbf45fbc78d9"
    
    hif_df = match_df[
        (match_df['TEAM_SSIID'] == hif_uuid) | 
        (match_df['TEAM_NAME'].str.contains("Hvidovre", case=False, na=False))
    ].copy()

    # Tjek om vi fandt Hvidovre i den valgte kamp
    if hif_df.empty:
        st.info(f"Ingen Hvidovre-specifikke data fundet for kampen: {valgt_kamp}")

    # Returner pakken til vis_side()
    return {
        "raw_stats": match_df,
        "hif_stats": hif_df,
        "match_name": valgt_kamp
    }
