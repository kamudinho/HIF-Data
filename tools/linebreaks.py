import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # --- 1. DATA HENTNING ---
    df_lb_raw = dp.get("opta_player_linebreaks", pd.DataFrame())
    name_map = dp.get("name_map", {})

    if df_lb_raw.empty:
        st.warning("⚠️ Ingen Linebreak-data fundet i 'opta_player_linebreaks'.")
        return

    # Standardiser kolonner
    df_lb_raw.columns = [c.upper() for c in df_lb_raw.columns]

    # --- 2. TRANSFORMATION (Fra 25 rækker til 1 række pr. spiller) ---
    # Vi pumper STAT_TYPE op som kolonner, så 'total', 'oneLine' osv. bliver overskrifter
    df_pivoted = df_lb_raw.pivot_table(
        index=['PLAYER_OPTAUUID', 'LINEUP_CONTESTANTUUID'], 
        columns='STAT_TYPE', 
        values='STAT_VALUE',
        aggfunc='sum'
    ).fillna(0).reset_index()

    # Navne-mapping og rensning
    df_pivoted['PLAYER_OPTAUUID'] = df_pivoted['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip()
    df_pivoted['NAVN'] = df_pivoted['PLAYER_OPTAUUID'].map(name_map).fillna(df_pivoted['PLAYER_OPTAUUID'])
    
    # Sorter efter 'total' linebreaks (hvis kolonnen findes)
    sort_col = 'total' if 'total' in df_pivoted.columns else df_pivoted.columns[-1]
    df_pivoted = df_pivoted.sort_values(sort_col, ascending=False)

    # --- 3. UI LAYOUT ---
    st.title("Linebreak Analyse")

    # Top-oversigt (Den brede tabel)
    st.subheader("Truppens Linebreak-performance")
    
    # Vi vælger de mest interessante kolonner til hovedtabellen
    cols_to_show = ['NAVN'] + [c for c in ['total', 'attackingLineBroken', 'midfieldLineBroken', 'defenceLineBroken'] if c in df_pivoted.columns]
    
    st.dataframe(
        df_pivoted[cols_to_show],
        use_container_width=True,
        hide_index=True
    )

    st.write("---")

    # --- 4. INDIVIDUEL SPILLER-DYK ---
    col_select, col_empty = st.columns([1, 2])
    with col_select:
        selected_navn = st.selectbox("Vælg spiller for detaljer", options=df_pivoted['NAVN'].tolist())
    
    p_uuid = df_pivoted[df_pivoted['NAVN'] == selected_navn]['PLAYER_OPTAUUID'].iloc[0]
    
    # Her går vi tilbage til de rå rækker for den valgte spiller for at lave grafen
    p_detail = df_lb_raw[df_lb_raw['PLAYER_OPTAUUID'].astype(str).str.lower().str.strip() == p_uuid].copy()

    c1, c2 = st.columns([2, 1])

    with c1:
        # Bar chart over typer (vi fjerner procenter og 'total' for at se fordelingen rent)
        chart_df = p_detail[
            (~p_detail['STAT_TYPE'].str.contains('percentage', case=False)) & 
            (p_detail['STAT_TYPE'] != 'total')
        ].sort_values('STAT_VALUE', ascending=True)

        fig = px.bar(
            chart_df, 
            x='STAT_VALUE', 
            y='STAT_TYPE', 
            orientation='h',
            title=f"Linebreak distribution: {selected_navn}",
            color_discrete_sequence=['#df003b']
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.write("**Alle Stats (FH/SH)**")
        # Her viser vi alle 25 rækker for den valgte spiller, så man kan se FH/SH detaljer
        st.dataframe(
            p_detail[['STAT_TYPE', 'STAT_VALUE', 'STAT_FH', 'STAT_SH']].sort_values('STAT_VALUE', ascending=False),
            use_container_width=True,
            hide_index=True,
            height=400
        )
