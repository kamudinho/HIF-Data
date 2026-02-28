import streamlit as st
import pandas as pd

def vis_side(df):
    # --- 1. FARVER & BRANDING (Matcher Scout DB) ---
    hif_rod = "#df003b"
    
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">TURNERING: KAMPOVERSIGT</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.info("Ingen data fundet for den valgte sæson.")
        return

    # --- 2. DATABEHANDLING ---
    # Sørg for at datoen er korrekt formateret
    df['DATE_DT'] = pd.to_datetime(df['DATE'])
    df = df.sort_values(by='DATE_DT', ascending=False)
    df['Dato'] = df['DATE_DT'].dt.strftime('%d-%m-%Y')

    # --- 3. FORBEREDELSE AF TABEL (Matcher Scout DB layout) ---
    # Vi udvælger og omdøber kolonner for at få et rent look
    disp = df[['Dato', 'GAMEWEEK', 'MATCHLABEL', 'TEAMNAME', 'GOALS', 'XG', 'SHOTS', 'SHOTSONTARGET']].copy()
    disp.columns = ['Dato', 'Rd.', 'Kamp', 'Hold', 'Mål', 'xG', 'Skud', 'På Mål']

    # Dynamisk højde ligesom i Scout DB
    tabel_hoejde = (len(disp) + 1) * 35 + 10 

    # --- 4. VISNING AF TABEL ---
    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True,
        height=tabel_hoejde,
        column_config={
            "Dato": st.column_config.TextColumn("Dato", width="small"),
            "Rd.": st.column_config.NumberColumn("Rd.", width="small"),
            "xG": st.column_config.NumberColumn("xG", format="%.2f"),
            "Mål": st.column_config.NumberColumn("Mål", format="%d")
        }
    )

    # --- 5. BUND-INFO ---
    st.divider()
    if not df.empty:
        st.caption(f"Sæson: {df['SEASONNAME'].iloc[0]} | Antal rækker: {len(df)}")
