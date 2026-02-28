import streamlit as st
import pandas as pd

def vis_side(df):
    # --- 1. FARVER & BRANDING (Præcis som Scout DB) ---
    hif_rod = "#df003b"
    
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">TURNERING: KAMPOVERSIGT</h3>
        </div>
    """, unsafe_allow_html=True)
    
    if df is None or df.empty:
        st.info("Ingen data fundet for den valgte sæson.")
        return

    # --- 2. DATABEHANDLING & BEREGNING AF HOLD ---
    df['DATE_DT'] = pd.to_datetime(df['DATE'])
    df = df.sort_values(by='DATE_DT', ascending=False)
    df['Dato'] = df['DATE_DT'].dt.strftime('%d-%m-%Y')

    # Vi finder alle unikke holdnavne fra MATCHLABEL (f.eks. "Hvidovre - B.93")
    # Vi splitter ved " - " og samler alle unikke navne til dropdown
    alle_hold = set()
    for label in df['MATCHLABEL'].dropna().unique():
        parts = label.split(' - ')
        for p in parts:
            alle_hold.add(p.strip())
    
    valgbare_hold = sorted(list(alle_hold))

    # --- 3. FILTER SEKTION ---
    col_filter, col_empty = st.columns([1, 2])
    with col_filter:
        valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + valgbare_hold)

    # Filtrering baseret på dropdown
    if valgt_hold != "Alle hold":
        # Vi filtrerer MATCHLABEL, så vi ser alle rækker der tilhører den kamp holdet deltog i
        mask = df['MATCHLABEL'].str.contains(valgt_hold, na=False)
        f_df = df[mask].copy()
    else:
        f_df = df.copy()

    # --- 4. FORBEREDELSE AF VISNING ---
    # Vi omdøber for at matche dit rene tabel-look
    disp = f_df[['Dato', 'GAMEWEEK', 'MATCHLABEL', 'TEAMNAME', 'GOALS', 'XG', 'SHOTS']].copy()
    disp.columns = ['Dato', 'Rd.', 'Kamp', 'Statistik for', 'Mål', 'xG', 'Skud']

    tabel_hoejde = (len(disp) + 1) * 35 + 10 

    # --- 5. VISNING ---
    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True,
        height=min(tabel_hoejde, 800), # Vi sætter et max på 800px så det ikke bliver uendeligt
        column_config={
            "Dato": st.column_config.TextColumn("Dato", width="small"),
            "Rd.": st.column_config.NumberColumn("Rd.", width="small"),
            "xG": st.column_config.NumberColumn("xG", format="%.2f"),
            "Mål": st.column_config.NumberColumn("Mål", format="%d")
        }
    )

    st.divider()
    st.caption(f"Viser {len(disp)} rækker | Sæson: {df['SEASONNAME'].iloc[0]}")
