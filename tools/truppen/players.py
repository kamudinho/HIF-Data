import streamlit as st
import pandas as pd
from datetime import datetime

def vis_side(df_raw):
    # --- DIAGNOSE: Hvad modtager vi egentlig? ---
    if df_raw is None:
        st.error("FEJL: Modulet modtager 'None' i stedet for data.")
        return
    
    if isinstance(df_raw, pd.DataFrame) and df_raw.empty:
        st.warning("ADVARSEL: Dataframen er tom (0 rækker). Tjek players.csv.")
        return

    # --- 1. RENS KOLONNER ---
    df = df_raw.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]
    
    # Vi tjekker om 'NAVN' findes, ellers prøver vi at finde en kolonne der minder om det
    navne_kolonne = 'NAVN' if 'NAVN' in df.columns else None
    if not navne_kolonne:
        # Hvis 'NAVN' ikke findes, tager vi den første kolonne der indeholder ordet 'NAME' eller 'NAVN'
        for c in df.columns:
            if 'NAV' in c or 'NAME' in c:
                navne_kolonne = c
                break
    
    if not navne_kolonne:
        st.error(f"Kunne ikke finde en navne-kolonne. Tilgængelige kolonner: {list(df.columns)}")
        st.write("Rå data preview:", df.head()) # Viser de første 5 rækker så vi kan se fejlen
        return

    # --- 2. FORBEREDELSE AF VISNING (Uden styling for at undgå 'duplicate keys') ---
    # Vi fjerner dubletter hårdt her
    df = df.dropna(subset=[navne_kolonne]).drop_duplicates(subset=[navne_kolonne]).reset_index(drop=True)

    # Vi bygger en simpel tabel for at se om det virker
    view_df = pd.DataFrame({
        'Spiller': df[navne_kolonne],
        'Position': df['POS'].fillna("-") if 'POS' in df.columns else "-",
        'Klub': df['TEAMNAME'].fillna("HIF") if 'TEAMNAME' in df.columns else "HIF",
        'Udløb': df['KONTRAKT'].fillna("-") if 'KONTRAKT' in df.columns else "-"
    })

    # --- 3. VISNING ---
    st.success(f"Indlæst {len(view_df)} spillere.")
    
    st.dataframe(
        view_df,
        use_container_width=True,
        hide_index=True,
        height=800
    )

    # Vis rå data i en expander til fejlfinding
    with st.expander("Se rå data (Debug)"):
        st.write(df_raw.head(10))
