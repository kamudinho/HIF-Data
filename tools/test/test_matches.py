import streamlit as st
import pandas as pd
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

    # --- 2. RENS NAVNE (Standardiserer til store bogstaver internt) ---
    df.columns = [c.upper() for c in df.columns]
    
    # Lav 'Kamp_Renset' baseret på hvad der findes
    if 'MATCHLABEL' in df.columns:
        df['Kamp_Renset'] = df['MATCHLABEL'].str.split(',').str[0]
    else:
        df['Kamp_Renset'] = df.get('CONTESTANTHOME_NAME', 'Hjemme') + " - " + df.get('CONTESTANTAWAY_NAME', 'Ude')

    valgbare_hold = sorted(list(TEAMS.keys()))

    # --- 3. FILTER ---
    c1, c2 = st.columns([1, 2])
    with c1:
        hvi_idx = valgbare_hold.index("Hvidovre IF") + 1 if "Hvidovre IF" in valgbare_hold else 0
        valgt_hold = st.selectbox("Vælg dit hold", ["Alle hold"] + valgbare_hold, index=hvi_idx)

    # --- 4. FILTRERING ---
    f_df = df[df['Kamp_Renset'].str.contains(valgt_hold, na=False)].copy() if valgt_hold != "Alle hold" else df.copy()

    # --- 5. DATO & RESULTAT-LOGIK (Her fixer vi fejlene) ---
    # Vi bruger .get() for at undgå 'KeyError' hvis Snowflake har ændret navnet
    f_df['DATE_DT'] = pd.to_datetime(f_df.get('DATE', f_df.get('MATCH_DATE_FULL', pd.Timestamp.now())))
    f_df = f_df.sort_values('DATE_DT', ascending=False)
    f_df['VisningsDato'] = f_df['DATE_DT'].dt.strftime('%d-%m-%Y')

    def get_score(row):
        # Tjek status - Opta bruger ofte 'Played' eller 'Closed'
        status = str(row.get('MATCH_STATUS', '')).strip()
        if status not in ['Played', 'Closed']:
            return "-"
        
        # Forsøg at finde mål i alle tænkelige kolonner fra din SQL
        h = row.get('TOTAL_HOME_SCORE', row.get('FT_HOME_SCORE', row.get('HOME_GOALS')))
        a = row.get('TOTAL_AWAY_SCORE', row.get('FT_AWAY_SCORE', row.get('AWAY_GOALS')))
        
        if pd.notna(h) and pd.notna(a):
            return f"{int(float(h))} - {int(float(a))}"
        return "-"

    f_df['Mål'] = f_df.apply(get_score, axis=1)

    # --- 6. INFO-TEKST ---
    with c2:
        st.markdown("<div style='padding-top: 25px;'></div>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style="text-align: right; color: rgba(49, 51, 63, 0.6); font-size: 0.8rem;">
                Viser {len(f_df)} kampe for {valgt_hold}
            </div>
        """, unsafe_allow_html=True)

    # --- 7. TABEL-VISNING (Brug de nye navne her) ---
    # Vi vælger de kolonner vi lige har skabt
    final_cols = ['VisningsDato', 'WEEK', 'Kamp_Renset', 'Mål', 'XG', 'SHOTS']
    
    # Sikr os at alle kolonner findes i dataframe før visning (fallback til 0)
    for col in final_cols:
        if col not in f_df.columns:
            f_df[col] = 0 if col in ['XG', 'SHOTS', 'WEEK'] else "-"

    disp = f_df[final_cols].copy()
    disp.columns = ['Dato', 'Rd.', 'Kamp', 'Mål', 'xG', 'Skud']

    st.dataframe(
        disp,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Dato": st.column_config.TextColumn(width="small"),
            "Rd.": st.column_config.NumberColumn(width="small"),
            "xG": st.column_config.NumberColumn(format="%.2f"),
        }
    )
