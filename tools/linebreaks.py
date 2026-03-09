def vis_side(dp):
    df = dp.get("player_linebreaks", pd.DataFrame())
    # Hent name_map og sørg for at alle nøgler er strings, lowercase og strippet for mellemrum
    raw_name_map = dp.get("name_map", {})
    name_map = {str(k).lower().strip(): str(v) for k, v in raw_name_map.items()}

    if df.empty:
        st.warning("Ingen data fundet.")
        return

    # Lav en kopi så vi ikke ændrer i originalen
    df = df.copy()
    df.columns = [c.upper() for c in df.columns]
    
    # Debug: Hvis du vil se om mappingen overhovedet indeholder noget
    # st.write(f"Antal navne i map: {len(name_map)}")

    # Map navne - vi stripper og lowercaser også UUID'en fra Snowflake for at sikre match
    df['SPILLER_NAVN'] = (
        df['PLAYER_OPTAUUID']
        .astype(str)
        .str.lower()
        .str.strip()
        .map(name_map)
        .fillna(df['PLAYER_OPTAUUID']) # Behold UUID hvis navn ikke findes
    )

    # Vis tabellen med det nye navn
    st.subheader("Truppens Linebreak-performance")
    display_df = df[['SPILLER_NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE']].copy()
    display_df.columns = ['Spiller', 'Total', 'Angrebslinje', 'Midtbane', 'Forsvar']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
