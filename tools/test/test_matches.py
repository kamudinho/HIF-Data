import streamlit as st
import pandas as pd
from data.utils.team_mapping import TEAMS

def vis_side(df):
    # 1. VIS OVERSKRIFT MED DET SAMME (Hvis denne ikke ses, dør den før funktionen)
    st.subheader("KAMPOVERSIGT")

    # 2. TOTAL SIKRING MOD TOM DATA
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("Ingen data fundet.")
        return

    try:
        # Lav en kopi og tving alle kolonnenavne til STORE BOGSTAVER
        df = df.copy()
        df.columns = [c.upper() for c in df.columns]

        # --- 3. DYNAMISK FILTER (Kun hold fra den aktuelle data) ---
        # Vi trækker navnene direkte fra hjemme- og udebane kolonnerne i din data
        if 'CONTESTANTHOME_NAME' in df.columns and 'CONTESTANTAWAY_NAME' in df.columns:
            hjemme = df['CONTESTANTHOME_NAME'].dropna().unique()
            ude = df['CONTESTANTAWAY_NAME'].dropna().unique()
            liga_hold = sorted(list(set(hjemme) | set(ude)))
        else:
            # Fallback hvis kolonnenavnene er anderledes (f.eks. i Wyscout data)
            # Vi prøver at trække navne ud fra MATCHLABEL (f.eks. "Hvidovre - Køge")
            labels = df['KAMP_NAVN'].str.split(' - ').str[0].dropna().unique()
            liga_hold = sorted(list(labels))

        # Vi finder Hvidovre i den nye korte liste så den er pre-selected
        hvi_index = 0
        for i, h in enumerate(liga_hold):
            if "Hvidovre" in str(h):
                hvi_index = i + 1 # +1 fordi vi har "Alle hold" øverst
                break

        valgt_hold = st.selectbox("Vælg hold", ["Alle hold"] + liga_hold, index=hvi_index)

        # 4. KONVERTER ALT TIL STRENG (Fjerner risiko for NaN-fejl)
        # Vi laver 'KAMP' kolonnen råt
        if 'MATCHLABEL' in df.columns:
            df['KAMP_NAVN'] = df['MATCHLABEL'].astype(str)
        elif 'CONTESTANTHOME_NAME' in df.columns:
            df['KAMP_NAVN'] = df['CONTESTANTHOME_NAME'].astype(str) + " - " + df['CONTESTANTAWAY_NAME'].astype(str)
        else:
            df['KAMP_NAVN'] = "Ukendt Kamp"

        # --- 5. UDFØR FILTER ---
        if valgt_hold != "Alle hold":
            # Direkte match fungerer bedst her, da navnene kommer direkte fra dataen
            f_df = df[(df['KAMP_NAVN'].str.contains(valgt_hold, case=False, na=False))].copy()
        else:
            f_df = df.copy()

        # 6. RESULTAT (Super simpel logik)
        # Vi henter værdier og bruger 0 hvis de mangler
        h_score = df.get('TOTAL_HOME_SCORE', df.get('HOME_GOALS', 0))
        a_score = df.get('TOTAL_AWAY_SCORE', df.get('AWAY_GOALS', 0))
        
        # Vi bygger resultatet manuelt som tekst
        df['MÅL'] = h_score.astype(str) + " - " + a_score.astype(str)
        df['MÅL'] = df['MÅL'].replace("nan - nan", "-") # Fix hvis begge er tomme

        # 7. DATO (Rå konvertering)
        dato_col = next((c for c in ['MATCH_DATE_FULL', 'DATE'] if c in df.columns), None)
        if dato_col:
            df['DATO_STR'] = df[dato_col].astype(str).str[:10] # Tag kun de første 10 tegn (YYYY-MM-DD)
        else:
            df['DATO_STR'] = "-"

        # 8. VISNING (Vi bruger kun de 3 vigtigste kolonner)
        final_df = df[['DATO_STR', 'KAMP_NAVN', 'MÅL']].copy()
        final_df.columns = ['Dato', 'Kamp', 'Mål']

        # Beregn højde (Max 800px for at være sikker)
        hoejde = min((len(final_df) * 35) + 45, 800)

        st.dataframe(
            final_df,
            use_container_width=True,
            hide_index=True,
            height=hoejde
        )

    except Exception as e:
        # Hvis noget går galt, skriver den fejlen i stedet for at gå i hvidt
        st.error(f"Der skete en fejl i tabel-genereringen: {e}")
