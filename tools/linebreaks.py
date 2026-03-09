import streamlit as st
import pandas as pd

def vis_side(dp):
    # 1. HENT DATA (Ret nøglen til 'player_linebreaks' så det matcher analyse_load)
    df = dp.get("player_linebreaks", pd.DataFrame())
    
    # 2. NAVNE-MAPPING
    raw_name_map = dp.get("name_map", {})
    name_map = {str(k).lower().strip(): v for k, v in raw_name_map.items()}

    if df.empty:
        st.warning("Fandt ingen linebreak-data. Prøver at vise rå-data for fejlfinding...")
        st.write(df) # Dette viser kolonnenavne hvis DF findes men er tom
        return

    # 3. RENS KOLONNER (Snowflake returnerer altid UPPERCASE)
    df.columns = [c.upper() for c in df.columns]

    # 4. MAP NAVNE (Brug PLAYER_OPTAUUID til at finde navnet fra players.csv)
    if 'PLAYER_OPTAUUID' in df.columns:
        df['PLAYER_OPTAUUID_CLEAN'] = df['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip()
        df['NAVN'] = df['PLAYER_OPTAUUID_CLEAN'].map(name_map).fillna(df['PLAYER_OPTAUUID'])
    else:
        df['NAVN'] = "Ukendt Spiller"

    st.title("🛡️ Hvidovre IF - Linebreak Analyse")

    # 5. TJEK FOR KOLONNER (Da vi lige har kørt en 'SELECT * LIMIT 100' uden CASE WHEN)
    # Hvis du kører din test-query uden pivotering, skal vi bruge de rå kolonner
    if 'STAT_TYPE' in df.columns:
        st.info("Viser rå Opta-data (ikke-pivoteret)")
        st.dataframe(df.head(20))
    else:
        # Hvis du har genindsat din MAX(CASE...) SQL, kører vi denne:
        df = df.sort_values('LB_TOTAL', ascending=False) if 'LB_TOTAL' in df.columns else df
        
        st.subheader("Truppens Overblik")
        vis_cols = [c for c in ['NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE'] if c in df.columns]
        st.dataframe(df[vis_cols], use_container_width=True, hide_index=True)

        # Metrikker for valgt spiller
        valgt = st.selectbox("Vælg spiller", df['NAVN'].unique())
        p = df[df['NAVN'] == valgt].iloc[0]
        
        c1, c2, c3 = st.columns(3)
        if 'LB_TOTAL' in p: c1.metric("Total", int(p['LB_TOTAL']))
        if 'TOTAL_LB_FH' in p: c2.metric("1. Halvleg", int(p['TOTAL_LB_FH']))
        if 'TOTAL_LB_SH' in p: c3.metric("2. Halvleg", int(p['TOTAL_LB_SH']))
