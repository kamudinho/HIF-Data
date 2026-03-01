import streamlit as st
import pandas as pd
from datetime import datetime
from data.utils.team_mapping import TEAMS

def vis_side(df):
    st.subheader("KAMPOVERSIGT")

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("Ingen data fundet.")
        return

    try:
        df = df.copy()
        df.columns = [c.upper() for c in df.columns]

        # --- 1. FILTRERING AF FREMTIDIGE KAMPE ---
        # Vi finder dato-kolonnen
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE'] if c in df.columns), None)
        
        if dato_col:
            # Konvertér til datetime (håndterer både strenge og objekter)
            df[dato_col] = pd.to_datetime(df[dato_col])
            # Vi beholder kun kampe, hvor datoen er før eller lig med 'nu'
            # (Du kan også bruge status-kolonnen 'PLAYED'/'RESULT' hvis tilgængelig)
            df = df[df[dato_col] <= datetime.now()].copy()

        # --- 2. LIGA-FILTER (ID 328) ---
        if 'COMPETITION_WYID' in df.columns:
            df = df[df['COMPETITION_WYID'] == 328].copy()
        elif 'COMPETITION_ID' in df.columns:
             df = df[df['COMPETITION_ID'] == 328].copy()

        if df.empty:
            st.info("Ingen spillede kampe fundet for NordicBet Liga (ID 328).")
            return

        # --- 3. KLARGØR NAVNE OG HOLDLISTE ---
        if 'MATCHLABEL' in df.columns:
            df['KAMP_NAVN'] = df['MATCHLABEL'].astype(str)
        elif 'CONTESTANTHOME_NAME' in df.columns:
            df['KAMP_NAVN'] = df['CONTESTANTHOME_NAME'].astype(str) + " - " + df['CONTESTANTAWAY_NAME'].astype(str)
        else:
            df['KAMP_NAVN'] = "Ukendt Kamp"

        # Dynamisk holdliste baseret på spillede kampe
        if 'CONTESTANTHOME_NAME' in df.columns:
            liga_hold = sorted(list(set(df['CONTESTANTHOME_NAME'].dropna()) | set(df['CONTESTANTAWAY_NAME'].dropna())))
        else:
            liga_hold = sorted(df['KAMP_NAVN'].str.split(' - ').str[0].unique())

        hvi_index = next((i + 1 for i, h in enumerate(liga_hold) if "Hvidovre" in str(h)), 0)
        valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + liga_hold, index=hvi_index)

        # --- 4. FILTRERING OG FORMATERING ---
        f_df = df.copy()
        if valgt_hold != "Alle hold":
            f_df = f_df[f_df['KAMP_NAVN'].str.contains(valgt_hold, case=False, na=False)].copy()

        # Sorter efter dato (nyeste øverst)
        if dato_col:
            f_df = f_df.sort_values(by=dato_col, ascending=False)

        # Mål-logik
        h_score = f_df.get('TOTAL_HOME_SCORE', f_df.get('HOME_GOALS', 0))
        a_score = f_df.get('TOTAL_AWAY_SCORE', f_df.get('AWAY_GOALS', 0))
        f_df['MÅL'] = h_score.astype(str).str.replace('.0', '', regex=False) + " - " + a_score.astype(str).str.replace('.0', '', regex=False)
        f_df['MÅL'] = f_df['MÅL'].replace("nan - nan", "-")

        f_df['DATO_STR'] = f_df[dato_col].dt.strftime('%d-%m-%Y') if dato_col else "-"

        # --- 5. VISNING ---
        final_df = f_df[['DATO_STR', 'KAMP_NAVN', 'MÅL']].copy()
        final_df.columns = ['Dato', 'Kamp', 'Mål']

        st.dataframe(
            final_df,
            use_container_width=True,
            hide_index=True,
            height=min((len(final_df) * 35) + 45, 800)
        )

    except Exception as e:
        st.error(f"Der skete en fejl i tabel-genereringen: {e}")
