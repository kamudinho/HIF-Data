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

    # --- 2. FORBERED GRUNDDATA ---
    df['Kamp_Renset'] = df['MATCHLABEL'].str.split(',').str[0]
    alle_hold = sorted(list(set([p.strip() for label in df['Kamp_Renset'].dropna().unique() for p in label.split(' - ')])))

    # --- 3. FILTER & INFO LINJE (To kolonner) ---
    c1, c2 = st.columns([1, 2])
    
    with c1:
        default_index = valgbare_hold.index("Hvidovre") + 1 if "Hvidovre" in alle_hold else 0
        valgt_hold = st.selectbox("Vælg dit hold", ["Alle hold"] + alle_hold, index=default_index)

    # --- 4. FILTRERING ---
    if valgt_hold != "Alle hold":
        kampe_id_liste = df[df['Kamp_Renset'].str.contains(valgt_hold, na=False)]['MATCH_WYID'].unique()
        f_df = df[df['MATCH_WYID'].isin(kampe_id_liste)].copy()
        f_df = f_df.drop_duplicates(subset=['MATCH_WYID'])
    else:
        f_df = df.copy()

    # --- 5. INFO TEKST (Placeret i højre kolonne c2) ---
    with c2:
        # Vi rykker teksten lidt ned så den flugter med selectboxen
        st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        tomme_stats = f_df[f_df['XG'].isna() | (f_df['XG'] == 0)].shape[0]
        
        info_str = f"📊 **{len(f_df)} unikke kampe for {valgt_hold}**"
        if tomme_stats > 0:
            info_str += f" | ⚠️ **{tomme_stats} mangler data**"
        
        st.write(info_str)

    # --- 6. KLARGØR VISNING & TABEL ---
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
