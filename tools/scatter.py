import streamlit as st
import plotly.express as px
import pandas as pd
from data.data_load import get_team_colors

# --- 2. FARVER & KONSTANTER ---
hif_rod = "#df003b"

    # --- TOP BRANDING ---
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">SCATTERPLOTS</h3>
        </div>
    """, unsafe_allow_html=True)

def build_scatter_plot(df_plot, x_label, y_label):
    from data.data_load import get_team_colors
    colors_dict = get_team_colors()
    
    # FIX: Plotly kan ikke lide ordbøger i ordbøger. 
    # Vi trækker kun 'primary' hex-koden ud.
    simple_colors = {team: (val["primary"] if isinstance(val, dict) else val) 
                     for team, val in colors_dict.items()}
    
    fig = px.scatter(
        df_plot, 
        x='X_PER_GAME', 
        y='Y_PER_GAME',
        hover_name='TEAMNAME',
        text='TEAMNAME', 
        color='TEAMNAME',
        color_discrete_map=simple_colors, # Brug det rensede map her
        height=700,
        template="plotly_white"
    )

    # Vender Y-aksen hvis det er en "IMOD/MOD" kategori (f.eks. færre mål imod er bedre)
    if any(word in y_label.upper() for word in ["MOD", "IMOD", "CONCEDED", "AGAINST"]):
        fig.update_yaxes(autorange="reversed")
    else:
        fig.update_yaxes(autorange=True)
    
    # --- HOVER-BOKS ---
    fig.update_traces(
        marker=dict(size=14, opacity=0.8, line=dict(width=1, color='DarkSlateGrey')),
        textposition='top center',
        hovertemplate=(
            "<b>%{hovertext}</b><br>" + 
            f"{x_label}: %{{x:.2f}}<br>" + 
            f"{y_label}: %{{y:.2f}}<br>" + 
            "<extra></extra>" 
        )
    )

    # --- AKSER ---
    fig.update_layout(
        showlegend=False,
        xaxis=dict(title=dict(text=f"{x_label} pr. kamp", font=dict(size=14, color="black")), zeroline=False),
        yaxis=dict(title=dict(text=f"{y_label} pr. kamp", font=dict(size=14, color="black")), zeroline=False),
        margin=dict(l=50, r=50, t=50, b=50)
    )

    # Gennemsnitslinjer (Quadrants)
    avg_x = df_plot['X_PER_GAME'].mean()
    avg_y = df_plot['Y_PER_GAME'].mean()
    fig.add_hline(y=avg_y, line_dash="dot", line_color="grey", opacity=0.5)
    fig.add_vline(x=avg_x, line_dash="dot", line_color="grey", opacity=0.5)
    
    return fig

def vis_side(df_scatter):
    if df_scatter is None or df_scatter.empty:
        st.warning("Ingen scatter-data tilgængelige.")
        return

    # 1. Forbered data
    df_s = df_scatter.copy()
    df_s.columns = [c.upper() for c in df_s.columns]
    
    # Sikrer os vi har de rigtige kolonnenavne fra din nye SQL
    # MATCHES kommer som TOTALPLAYED i din SQL, men vi renamer den her for en sikkerheds skyld
    if 'TOTALPLAYED' in df_s.columns and 'MATCHES' not in df_s.columns:
        df_s = df_s.rename(columns={'TOTALPLAYED': 'MATCHES'})

    # 2. Definition af Metrics (Menu-navn: Kolonne_X, Kolonne_Y, Label_X, Label_Y)
    # Tilføjet PASSESTOFINALTHIRD som vi lige har fået adgang til
    metric_options = {
        "MÅL FOR vs. MÅL IMOD": ("GOALS", "CONCEDEDGOALS", "MÅL FOR", "MÅL IMOD"),
        "xG FOR vs. xG IMOD": ("XGSHOT", "XGSHOTAGAINST", "xG FOR", "xG IMOD"),
        "SKUD vs. xG": ("SHOTS", "XGSHOT", "SKUD", "xG"),
        "PASNINGER 3. DEL vs. xG": ("PASSESTOFINALTHIRD", "XGSHOT", "PASSES SIDSTE 3.DEL", "xG")
    }

    # 3. UI
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">SCATTERPLOTS - STRATEGISK OVERBLIK</h3>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        # Hvis du ikke har COMPETITIONNAME i din team_stats_full, kan vi bare vise den aktuelle data
        leagues = sorted(df_s['COMPETITIONNAME'].unique()) if 'COMPETITIONNAME' in df_s.columns else ["Betinia Ligaen"]
        st.selectbox("Vælg Turnering", leagues, disabled=len(leagues)==1)
    with c2:
        metric_type = st.selectbox("Vælg Analyse", list(metric_options.keys()))

    # 4. Beregning
    x_raw, y_raw, label_x, label_y = metric_options[metric_type]
    
    # Sikkerhedstjek for manglende kolonner
    for col in [x_raw, y_raw, 'MATCHES']:
        if col not in df_s.columns:
            df_s[col] = 0
        df_s[col] = pd.to_numeric(df_s[col], errors='coerce').fillna(0)

    df_s['X_PER_GAME'] = df_s[x_raw] / df_s['MATCHES'].replace(0, 1)
    df_s['Y_PER_GAME'] = df_s[y_raw] / df_s['MATCHES'].replace(0, 1)

    # 5. Plot
    fig = build_scatter_plot(df_s, label_x, label_y)
    st.plotly_chart(fig, use_container_width=True)
