import streamlit as st
import pandas as pd

def vis_side(df):
    # --- 1. BRANDING (Scout DB Style) ---
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
    # Vi fjerner resultatet (alt efter kommaet)
    df['Kamp_Renset'] = df['MATCHLABEL'].str.split(',').str[0]
    
    # Find alle unikke hold fra de rensede labels
    alle_hold = set()
    for label in df['Kamp_Renset'].dropna().unique():
        parts = label.split(' - ')
        for p in parts:
            alle_hold.add(p.strip())
    
    valgbare_hold = sorted(list(alle_hold))

    # --- 3. FILTER ---
    c1, _ = st.columns([1, 2])
    with c1:
        valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + valgbare_hold)

    # Filtrering
    if valgt_hold != "Alle hold":
        f_df = df[df['Kamp_Renset'].str.contains(valgt_hold, na=False)].copy()
    else:
        f_df = df.copy()

    # Sortering
    f_df['DATE_DT'] = pd.to_datetime(f_df['DATE'])
    f_df = f_df.sort_values('DATE_DT', ascending=False)
    f_df['Dato'] = f_df['DATE_DT'].dt.strftime('%d-%m-%Y')

    # --- 4. KLARGØR VISNING (Bruger de korrekte SQL-kolonnenavne) ---
    # Da TEAMNAME mangler i din SQL, bruger vi MATCHLABEL som reference
    disp = f_df[['Dato', 'GAMEWEEK', 'Kamp_Renset', 'GOALS', 'XG', 'SHOTS', 'SHOTSONTARGET']].copy()
    disp.columns = ['Dato', 'Rd.', 'Kamp', 'Mål', 'xG', 'Skud', 'På mål']

    # --- 5. TABEL ---
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
    st.caption(f"Viser data for {valgt_hold} | Sæson: {df['SEASONNAME'].iloc[0] if 'SEASONNAME' in df.columns else '2025/2026'}")
