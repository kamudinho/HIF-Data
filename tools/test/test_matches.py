import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(df):
    st.subheader("KAMPOVERSIGT")

    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("Ingen data fundet.")
        return

    try:
        df = df.copy()
        df.columns = [c.upper() for c in df.columns]

        # 1. LIGA-FILTER (ID 328)
        if 'COMPETITION_WYID' in df.columns:
            df = df[df['COMPETITION_WYID'] == 328].copy()
        elif 'COMPETITION_ID' in df.columns:
             df = df[df['COMPETITION_ID'] == 328].copy()

        if df.empty:
            st.info("Ingen kampe fundet for NordicBet Liga (ID 328).")
            return

        # 2. KLARGØR NAVNE FØR FILTER
        if 'MATCHLABEL' in df.columns:
            df['KAMP_NAVN'] = df['MATCHLABEL'].astype(str)
        elif 'CONTESTANTHOME_NAME' in df.columns:
            df['KAMP_NAVN'] = df['CONTESTANTHOME_NAME'].astype(str) + " - " + df['CONTESTANTAWAY_NAME'].astype(str)
        else:
            df['KAMP_NAVN'] = "Ukendt Kamp"

        # 3. DYNAMISK HOLD-LISTE
        if 'CONTESTANTHOME_NAME' in df.columns:
            hjemme = df['CONTESTANTHOME_NAME'].dropna().unique()
            ude = df['CONTESTANTAWAY_NAME'].dropna().unique()
            liga_hold = sorted(list(set(hjemme) | set(ude)))
        else:
            labels = df['KAMP_NAVN'].str.split(' - ').str[0].unique()
            liga_hold = sorted([x for x in labels if x and str(x) != 'nan'])

        hvi_index = 0
        for i, h in enumerate(liga_hold):
            if "Hvidovre" in str(h):
                hvi_index = i + 1
                break

        valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + liga_hold, index=hvi_index)

        # 4. UDFØR HOLD-FILTRERING (Her skaber vi f_df)
        if valgt_hold != "Alle hold":
            mask = (df['KAMP_NAVN'].str.contains(valgt_hold, case=False, na=False))
            f_df = df[mask].copy()
        else:
            f_df = df.copy()

        # 5. BEREGN RESULTAT OG DATO PÅ DEN FILTREREDE DATA (f_df)
        # Vi henter værdier fra f_df nu!
        h_score = f_df.get('TOTAL_HOME_SCORE', f_df.get('HOME_GOALS', 0))
        a_score = f_df.get('TOTAL_AWAY_SCORE', f_df.get('AWAY_GOALS', 0))
        
        f_df['MÅL'] = h_score.astype(str) + " - " + a_score.astype(str)
        f_df['MÅL'] = f_df['MÅL'].replace("nan - nan", "-")

        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE'] if c in f_df.columns), None)
        if dato_col:
            f_df['DATO_STR'] = f_df[dato_col].astype(str).str[:10]
        else:
            f_df['DATO_STR'] = "-"

        # 6. VISNING
        final_df = f_df[['DATO_STR', 'KAMP_NAVN', 'MÅL']].copy()
        final_df.columns = ['Dato', 'Kamp', 'Mål']

        hoejde = min((len(final_df) * 35) + 45, 800)

        st.dataframe(
            final_df,
            use_container_width=True,
            hide_index=True,
            height=hoejde
        )

    except Exception as e:
        st.error(f"Der skete en fejl i tabel-genereringen: {e}")
