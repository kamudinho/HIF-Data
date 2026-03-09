import streamlit as st
import pandas as pd
import plotly.express as px

def vis_side(dp):
    # 1. Hent data (som nu er pivoteret fra SQL)
    df = dp.get("opta_player_linebreaks", pd.DataFrame())
    name_map = dp.get("name_map", {})

    if df.empty:
        st.warning("⚠️ Ingen data fundet. Tjek din SQL-forbindelse.")
        return

    # Sørg for at kolonnenavne er store bogstaver for at matche Snowflake output
    df.columns = [c.upper() for c in df.columns]

    # Navne-mapping (Hvidovre-spillere)
    df['NAVN'] = df['PLAYER_OPTAUUID'].str.lower().str.strip().map(name_map).fillna(df['PLAYER_OPTAUUID'])

    # --- UI LAYOUT ---
    st.title("🛡️ Linebreak Analyse")
    st.markdown("Baseret på Opta-data: Evnen til at spille forbi modstanderens kæder.")

    # 2. Top-liste (Hele truppen)
    st.subheader("Truppens overblik")
    
    # Vi vælger de mest relevante kolonner til hurtigt overblik
    vis_cols = ['NAVN', 'LB_TOTAL', 'LB_ATTACK_LINE', 'LB_MIDFIELD_LINE', 'LB_DEFENCE_LINE', 'LB_PENALTY_AREA']
    
    # Sorter efter total og vis
    df_display = df.sort_values('LB_TOTAL', ascending=False)
    
    st.dataframe(
        df_display[vis_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "LB_TOTAL": st.column_config.NumberColumn("Total", help="Total antal linebreaks"),
            "LB_PENALTY_AREA": st.column_config.NumberColumn("Ind i feltet", format="%d 📥")
        }
    )

    st.divider()

    # 3. Individuel Spiller-dyk
    col_sel, col_empty = st.columns([1, 2])
    with col_sel:
        valgt_spiller = st.selectbox("Vælg spiller for detaljer", options=df_display['NAVN'].tolist())

    # Find data for den valgte spiller
    p_data = df_display[df_display['NAVN'] == valgt_spiller].iloc[0]

    # Metrics række
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Linebreaks", int(p_data['LB_TOTAL']))
    m2.metric("Under Pres", int(p_data.get('LB_UNDER_PRESSURE', 0)))
    m3.metric("1. Halvleg", int(p_data['TOTAL_LB_FH']))
    m4.metric("2. Halvleg", int(p_data['TOTAL_LB_SH']))

    # Visualisering af linebreak typer
    st.subheader(f"Fordeling for {valgt_spiller}")
    
    # Forbered data til graf (vi tager de specifikke LB kolonner)
    plot_data = pd.DataFrame({
        'Type': ['Mod Angreb', 'Mod Midtbane', 'Mod Forsvar', 'Ind i feltet'],
        'Antal': [
            p_data['LB_ATTACK_LINE'], 
            p_data['LB_MIDFIELD_LINE'], 
            p_data['LB_DEFENCE_LINE'], 
            p_data['LB_PENALTY_AREA']
        ]
    })

    fig = px.bar(
        plot_data, 
        x='Antal', 
        y='Type', 
        orientation='h',
        color='Antal',
        color_continuous_scale='Reds',
        text_auto=True
    )
    
    fig.update_layout(showlegend=False, height=350)
    st.plotly_chart(fig, use_container_width=True)
