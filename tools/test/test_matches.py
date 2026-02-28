import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS # Vigtigt til filtrering

def vis_side(df):
    # --- 1. BRANDING ---
    hif_rod = "#df003b"
    
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">TURNERING: KAMPOVERSIGT (OPTA/WY)</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.info("Ingen data fundet.")
        return

    # --- 2. RENS DATA BASERET PÅ KILDE ---
    # Opta bruger tit 'MATCHLABEL' direkte, men vi sikrer os at vi kan splitte den
    if 'MATCHLABEL' in df.columns:
        df['Kamp_Renset'] = df['MATCHLABEL'].str.split(',').str[0]
    else:
        # Hvis det er ren Opta data uden label, bygger vi den selv
        df['Kamp_Renset'] = df['HOME_TEAM_NAME'] + " - " + df['AWAY_TEAM_NAME']
    
    # Vi henter hold fra vores centrale mapping i stedet for at stole på rå data
    valgbare_hold = sorted(list(TEAMS.keys()))

    # --- 3. LAYOUT: FILTER ---
    c1, c2 = st.columns([1, 2])
    
    with c1:
        # Finder Hvidovre IF i listen
        hvi_idx = valgbare_hold.index("Hvidovre IF") + 1 if "Hvidovre IF" in valgbare_hold else 0
        valgt_hold = st.selectbox("Vælg dit hold", ["Alle hold"] + valgbare_hold, index=hvi_idx)

    # --- 4. FILTRERING (Understøtter både WYID og Opta UUID) ---
    if valgt_hold != "Alle hold":
        hvi_info = TEAMS.get(valgt_hold, {})
        wyid = hvi_info.get("team_wyid")
        uuid = hvi_info.get("opta_uuid")
        
        # Vi filtrerer på navnet i Kamp_Renset for at ramme begge kilder bredt
        f_df = df[df['Kamp_Renset'].str.contains(valgt_hold, na=False)].copy()
        
        # Hvis vi har ID'er, så dubbel-tjek for præcision
        if 'MATCH_WYID' in f_df.columns:
            f_df = f_df.drop_duplicates(subset=['MATCH_WYID'])
    else:
        f_df = df.copy()

    # --- 5. INFO-TEKST ---
    with c2:
        st.markdown("<div style='padding-top: 25px;'></div>", unsafe_allow_html=True)
        
        # xG håndtering (Opta kan have 0.00 hvis ikke beregnet endnu)
        mangler_mask = (f_df['XG'].isna()) | (f_df['XG'] < 0.01)
        tomme_stats = f_df[mangler_mask].shape[0]
        
        info_html = f"""
            <div style="text-align: right; color: rgba(49, 51, 63, 0.6); font-size: 0.8rem; line-height: 1.2;">
                Der er {len(f_df)} unikke kampe for {valgt_hold}<br>
                {"Obs: Mangler xG/Skud data på " + str(tomme_stats) + " kampe" if tomme_stats > 0 else "Alle stats er indlæst"}
            </div>
        """
        st.markdown(info_html, unsafe_allow_html=True)

    # --- 6. KLARGØR VISNING ---
    f_df['DATE_DT'] = pd.to_datetime(f_df['DATE'])
    f_df = f_df.sort_values('DATE_DT', ascending=False)
    f_df['Dato'] = f_df['DATE_DT'].dt.strftime('%d-%m-%Y')

    # Sikrer os at kolonnerne findes (hvis Opta-queryen f.eks. mangler SHOTS)
    for col in ['GOALS', 'XG', 'SHOTS', 'GAMEWEEK']:
        if col not in f_df.columns:
            f_df[col] = 0

    disp = f_df[['Dato', 'GAMEWEEK', 'Kamp_Renset', 'GOALS', 'XG', 'SHOTS']].copy()
    disp.columns = ['Dato', 'Rd.', 'Kamp', 'Mål', 'xG', 'Skud']

    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True,
        height=min((len(disp) + 1) * 35 + 10, 800),
        column_config={
            "Dato": st.column_config.TextColumn(width="small"),
            "Rd.": st.column_config.NumberColumn(width="small"),
            "xG": st.column_config.NumberColumn(format="%.2f"),
        }
    )

    st.divider()
    st.caption(f"Viser data fra {valgt_hold} (Kilde: Snowflake)")
