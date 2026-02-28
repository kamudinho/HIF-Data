import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(df):
    # --- 1. BRANDING ---
    hif_rod = "#cc0000"
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; text-transform:uppercase;">KAMPOVERSIGT</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.info("Ingen data fundet.")
        return

    # Standardiser kolonner til UPPERCASE (vigtigt for Snowflake data)
    df.columns = [c.upper() for c in df.columns]

    # --- 2. FORBERED DATA ---
    # Lav en ren kamp-tekst (Hjemme - Ude)
    if 'MATCHLABEL' in df.columns:
        df['KAMP_NAVN'] = df['MATCHLABEL'].str.split(',').str[0]
    else:
        # Hvis det er rå Opta data
        h = df.get('CONTESTANTHOME_NAME', 'Hjemme')
        a = df.get('CONTESTANTAWAY_NAME', 'Ude')
        df['KAMP_NAVN'] = h + " - " + a

    # --- 3. FILTRERING (Vælg hold) ---
    # Vi henter alle holdnavne fra din team_mapping.py
    alle_hold = sorted(list(TEAMS.keys()))
    
    col1, col2 = st.columns([1, 2])
    with col1:
        # Vi sætter "Hvidovre IF" som standard hvis det findes
        default_ix = alle_hold.index("Hvidovre IF") + 1 if "Hvidovre IF" in alle_hold else 0
        valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + alle_hold, index=default_ix)

    # Udfør filtreringen
    if valgt_hold != "Alle hold":
        mask = df['KAMP_NAVN'].str.contains(valgt_hold, case=False, na=False)
        f_df = df[mask].copy()
    else:
        f_df = df.copy()

    # --- 4. FORMATERING ---
    # Dato fix
    dato_col = next((c for c in ['DATE', 'MATCH_DATE_FULL'] if c in f_df.columns), None)
    if dato_col:
        f_df['DATO_VIS'] = pd.to_datetime(f_df[dato_col]).dt.strftime('%d-%m-%Y')
    
    # Mål/Resultat fix
    def format_score(row):
        h = row.get('TOTAL_HOME_SCORE', row.get('HOME_GOALS', 0))
        a = row.get('TOTAL_AWAY_SCORE', row.get('AWAY_GOALS', 0))
        if pd.isna(h) or pd.isna(a): return "-"
        return f"{int(h)} - {int(a)}"

    f_df['RESULTAT'] = f_df.apply(format_score, axis=1)

    # --- 5. VISNING UDEN SCROLL ---
    # Vi vælger de relevante kolonner
    disp = f_df[['DATO_VIS', 'WEEK', 'KAMP_NAVN', 'RESULTAT']].copy()
    disp.columns = ['Dato', 'Rd.', 'Kamp', 'Mål']

    # Beregn højden: ca. 35px pr. række + 40px til header
    # Hvis du har 30 kampe, bliver højden ca. 1100px.
    tabel_hoejde = (len(disp) * 35) + 40

    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True,
        height=tabel_hoejde, # HER fjerner vi scroll ved at sætte højden dynamisk
        column_config={
            "Dato": st.column_config.TextColumn(width="small"),
            "Rd.": st.column_config.NumberColumn(width="small")
        }
    )
