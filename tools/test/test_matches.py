import streamlit as st
import pandas as pd

def vis_side(df):
    # --- 1. BRANDING ---
    hif_rod = "#df003b"
    
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">TURNERING: KAMPOVERSIGT</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.info("Ingen data fundet.")
        return

    # --- 2. TJEK FOR MANGLENDE STATS (Placeres her for synlighed) ---
    # Vi tjekker om xG er 0 eller None i de nyeste kampe
    tomme_stats = df[df['XG'].isna() | (df['XG'] == 0)].shape[0]
    if tomme_stats > 0:
        st.warning(f"⚠️ Obs: {tomme_stats} rækker i databasen mangler xG/Skud data. Dette skyldes ofte forsinkelse fra Wyscout.")

    # --- 3. RENS MATCHLABEL OG FIND HOLD ---
    df['Kamp_Renset'] = df['MATCHLABEL'].str.split(',').str[0]
    
    alle_hold = set()
    for label in df['Kamp_Renset'].dropna().unique():
        parts = label.split(' - ')
        for p in parts:
            alle_hold.add(p.strip())
    
    valgbare_hold = sorted(list(alle_hold))

    # --- 4. FILTER SEKTION ---
    c1, _ = st.columns([1, 2])
    with c1:
        default_index = 0
        if "Hvidovre" in valgbare_hold:
            default_index = valgbare_hold.index("Hvidovre") + 1
        valgt_hold = st.selectbox("Vælg dit hold", ["Alle hold"] + valgbare_hold, index=default_index)

    # --- 5. FILTRERING & DUBLETHÅNDTERING ---
    if valgt_hold != "Alle hold":
        kampe_id_liste = df[df['Kamp_Renset'].str.contains(valgt_hold, na=False)]['MATCH_WYID'].unique()
        f_df = df[df['MATCH_WYID'].isin(kampe_id_liste)].copy()
        # drop_duplicates sikrer vi kun ser én række pr. kamp
        f_df = f_df.drop_duplicates(subset=['MATCH_WYID'])
    else:
        f_df = df.copy()

    f_df['DATE_DT'] = pd.to_datetime(f_df['DATE'])
    f_df = f_df.sort_values('DATE_DT', ascending=False)
    f_df['Dato'] = f_df['DATE_DT'].dt.strftime('%d-%m-%Y')

    # --- 6. KLARGØR VISNING ---
    disp = f_df[['Dato', 'GAMEWEEK', 'Kamp_Renset', 'GOALS', 'XG', 'SHOTS']].copy()
    disp.columns = ['Dato', 'Rd.', 'Kamp', 'Mål', 'xG', 'Skud']

    tabel_hoejde = (len(disp) + 1) * 35 + 10
    
    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True,
        height=min(tabel_hoejde, 800),
        column_config={
            "Dato": st.column_config.TextColumn(width="small"),
            "Rd.": st.column_config.NumberColumn(width="small"),
            "xG": st.column_config.NumberColumn(format="%.2f"),
        }
    )

    # --- 7. TÆLLER UNDER TABELLEN ---
    st.write(f"📊 **Der er {len(f_df)} kampe i databasen for det valgte filter.**")

    st.divider()
    st.caption(f"Viser unikke kampe for {valgt_hold}")

Her var der fokus på det, at det virkede. 
st.write og st.alert skal laves til st.caption og uden ikoner - disse skal stå helt ude til højre under branding
