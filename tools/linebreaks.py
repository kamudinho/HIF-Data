import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # Hent dataframe
    df = dp.get("opta_player_linebreaks", pd.DataFrame())
    
    # Hent name_map og sørg for at alle keys er lowercase
    raw_name_map = dp.get("name_map", {})
    name_map = {str(k).lower().strip(): v for k, v in raw_name_map.items()}

    if df.empty:
        st.error("⚠️ Ingen rækker returneret fra Snowflake. Tjek din SQL-query i 'get_opta_queries'.")
        return

    # Tving alle kolonnenavne i DF til UPPERCASE (standard Snowflake)
    df.columns = [c.upper() for c in df.columns]

    # Rens UUID'er og map navne
    # Vi bruger .astype(str) for at undgå problemer med typer
    df['PLAYER_OPTAUUID'] = df['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip()
    df['NAVN'] = df['PLAYER_OPTAUUID'].map(name_map).fillna(df['PLAYER_OPTAUUID'])

    # --- UI ---
    st.title("🛡️ Hvidovre IF - Linebreak Analyse")

    # Vis top 5 for at tjekke om data overhovedet er der
    st.subheader("Truppens Overblik")
    
    # Sortering (Vi bruger de navne din SQL producerede)
    df = df.sort_values('LB_TOTAL', ascending=False)

    # Konfigurer visning
    st.dataframe(
        df[['NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']],
        use_container_width=True,
        hide_index=True
    )

    # Spiller-vælger
    spiller_liste = df['NAVN'].unique().tolist()
    valgt = st.selectbox("Vælg spiller for detaljer", spiller_liste)
    
    # Spiller-data
    p = df[df['NAVN'] == valgt].iloc[0]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Linebreaks", int(p['LB_TOTAL']))
    c2.metric("1. Halvleg", int(p['TOTAL_LB_FH']))
    c3.metric("2. Halvleg", int(p['TOTAL_LB_SH']))
