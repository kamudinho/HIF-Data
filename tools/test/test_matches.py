import streamlit as st
import pandas as pd
import numpy as np
from data.utils.team_mapping import TEAMS

def vis_side(df):
    # --- 1. BRANDING ---
    hif_rod = "#df003b"
    
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">TURNERING: KAMPOVERSIGT (OPTA)</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.info("Ingen data fundet.")
        return

    # --- 2. RENS DATA ---
    if 'MATCHLABEL' in df.columns:
        df['Kamp_Renset'] = df['MATCHLABEL'].str.split(',').str[0]
    
    valgbare_hold = sorted(list(TEAMS.keys()))

    # --- 3. LAYOUT: FILTER ---
    c1, c2 = st.columns([1, 2])
    with c1:
        hvi_idx = valgbare_hold.index("Hvidovre IF") + 1 if "Hvidovre IF" in valgbare_hold else 0
        valgt_hold = st.selectbox("Vælg dit hold", ["Alle hold"] + valgbare_hold, index=hvi_idx)

    # --- 4. FILTRERING ---
    if valgt_hold != "Alle hold":
        f_df = df[df['Kamp_Renset'].str.contains(valgt_hold, na=False)].copy()
    else:
        f_df = df.copy()

    # --- 5. RESULTAT-LOGIK (Fixer "Cannot convert non-finite values") ---
    def format_score(row):
        # Hvis kampen ikke er spillet eller status er mærkelig
        if row.get('MATCH_STATUS') != 'Played':
            return "-"
            
        try:
            # Vi tjekker om begge værdier eksisterer og er tal (ikke NaN)
            h_val = row.get('TOTAL_HOME_SCORE')
            a_val = row.get('TOTAL_AWAY_SCORE')
            
            if pd.notna(h_val) and pd.notna(a_val):
                return f"{int(float(h_val))} - {int(float(a_val))}"
            return "-"
        except:
            return "-"

    f_df['Mål'] = f_df.apply(format_score, axis=1)

    # --- 6. INFO-TEKST ---
    with c2:
        st.markdown("<div style='padding-top: 25px;'></div>", unsafe_allow_html=True)
        mangler_mask = (f_df['XG'].isna()) | (f_df['XG'] < 0.01)
        tomme_stats = f_df[mangler_mask].shape[0]
        
        info_html = f"""
            <div style="text-align: right; color: rgba(49, 51, 63, 0.6); font-size: 0.8rem; line-height: 1.2;">
                Der er {len(f_df)} unikke kampe for {valgt_hold}<br>
                {"Obs: Mangler data på " + str(tomme_stats) + " rækker" if tomme_stats > 0 else ""}
            </div>
        """
        st.markdown(info_html, unsafe_allow_html=True)

    # --- 7. KLARGØR VISNING ---
    f_df['DATE_DT'] = pd.to_datetime(f_df['DATE'])
    f_df = f_df.sort_values('DATE_DT', ascending=False)
    f_df['Dato'] = f_df['DATE_DT'].dt.strftime('%d-%m-%Y')

    # Kolonnevalg
    disp = f_df[['Dato', 'GAMEWEEK', 'Kamp_Renset', 'Mål', 'XG', 'SHOTS']].copy()
    disp.columns = ['Dato', 'Rd.', 'Kamp', 'Mål', 'xG', 'Skud']

    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True,
        height=min((len(disp) + 1) * 35 + 10, 800),
        column_config={
            "Dato": st.column_config.TextColumn(width="small"),
            "Rd.": st.column_config.NumberColumn(width="small"),
            "Mål": st.column_config.TextColumn(width="small"),
            "xG": st.column_config.NumberColumn(format="%.2f"),
        }
    )

    st.divider()
    st.caption(f"Viser data fra {valgt_hold} (Kilde: Snowflake/Opta)")
