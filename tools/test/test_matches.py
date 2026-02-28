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

    # --- 2. FORBERED DATA ---
    df['Kamp_Renset'] = df['MATCHLABEL'].str.split(',').str[0]
    
    hold_set = set()
    for label in df['Kamp_Renset'].dropna().unique():
        parts = label.split(' - ')
        for p in parts:
            hold_set.add(p.strip())
    
    valgbare_hold = sorted(list(hold_set))

    # --- 3. FILTER & INFO SEKTION ---
    c1, c2 = st.columns([1, 2])
    
    with c1:
        default_index = 0
        if "Hvidovre" in valgbare_hold:
            default_index = valgbare_hold.index("Hvidovre") + 1
        valgt_hold = st.selectbox("Vælg dit hold", ["Alle hold"] + valgbare_hold, index=default_index)

    # --- 4. FILTRERING ---
    if valgt_hold != "Alle hold":
        kampe_id_liste = df[df['Kamp_Renset'].str.contains(valgt_hold, na=False)]['MATCH_WYID'].unique()
        f_df = df[df['MATCH_WYID'].isin(kampe_id_liste)].copy()
        f_df = f_df.drop_duplicates(subset=['MATCH_WYID'])
    else:
        f_df = df.copy()

    # --- 5. HØJRE SIDE (Nu baseret på xG) ---
    with c2:
        # Flyt captions ned så de flugter med selectboxen
        st.markdown("<div style='padding-top: 20px;'></div>", unsafe_allow_html=True)
        
        # Linje 1: Antal kampe
        st.caption(f"Der er {len(f_df)} unikke kampe for {valgt_hold}")
        
        # Linje 2: Manglende data (Beregnet på xG)
        # Vi tæller rækker i f_df hvor xG er NaN eller præcis 0.0
        mangler = f_df[f_df['XG'].isna() | (f_df['XG'] == 0)].shape[0]
        
        if mangler > 0:
            st.caption(f"⚠️ Obs: {mangler} rækker i databasen mangler data")

    # --- 6. TABEL ---
    f_df['DATE_DT'] = pd.to_datetime(f_df['DATE'])
    f_df = f_df.sort_values('DATE_DT', ascending=False)
    f_df['Dato'] = f_df['DATE_DT'].dt.strftime('%d-%m-%Y')

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
