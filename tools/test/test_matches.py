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

    # --- 2. RENS MATCHLABEL OG FIND HOLD ---
    # Vi splitter ved kommaet for at fjerne resultatet ", 2-1"
    df['Kamp_Renset'] = df['MATCHLABEL'].str.split(',').str[0]
    
    # Vi finder unikke holdnavne til dropdown
    alle_hold = set()
    for label in df['Kamp_Renset'].dropna().unique():
        parts = label.split(' - ')
        for p in parts:
            alle_hold.add(p.strip())
    
    valgbare_hold = sorted(list(alle_hold))

    # --- 3. FILTER SEKTION ---
    c1, _ = st.columns([1, 2])
    with c1:
        # Find index for Hvidovre hvis det findes, ellers 0
        default_index = 0
        if "Hvidovre" in valgbare_hold:
            default_index = valgbare_hold.index("Hvidovre") + 1
            
        valgt_hold = st.selectbox("Vælg dit hold", ["Alle hold"] + valgbare_hold, index=default_index)

    # --- 4. DEN VIGTIGE FILTRERING ---
    if valgt_hold != "Alle hold":
        # 1. Find alle kampe (MATCH_WYID) hvor det valgte hold har deltaget
        kampe_id_liste = df[df['Kamp_Renset'].str.contains(valgt_hold, na=False)]['MATCH_WYID'].unique()
        
        # 2. Vis kun rækkerne for det valgte hold i de kampe
        # Vi ved at MATCHLABEL altid starter med Hjemmehold - Udehold
        # Så vi tjekker om rækken i TEAMMATCHES (som din SQL bygger på) 
        # er den "rigtige" halvdel af kampen. 
        # Da TEAMNAME mangler i din query, kan vi bruge en lille genvej: 
        # Vi viser kun den række pr. kamp, hvor statistikken matcher det valgte holds præstation.
        
        # NOTE: For at dette skal være 100% fejlfrit, SKAL vi have TEAMNAME eller TEAM_WYID med i din SQL.
        # Men indtil da filtrerer vi på kampe, og grupperer så vi kun ser unikke kamp-rækker:
        f_df = df[df['MATCH_WYID'].isin(kampe_id_liste)].copy()
        
        # Hvis vi vil undgå dubletter, tager vi kun én række pr. MATCH_WYID
        f_df = f_df.drop_duplicates(subset=['MATCH_WYID'])
    else:
        f_df = df.copy()

    # Sortering efter dato
    f_df['DATE_DT'] = pd.to_datetime(f_df['DATE'])
    f_df = f_df.sort_values('DATE_DT', ascending=False)
    f_df['Dato'] = f_df['DATE_DT'].dt.strftime('%d-%m-%Y')

    # --- 5. KLARGØR VISNING ---
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

    st.divider()
    st.caption(f"Viser unikke kampe for {valgt_hold}")
