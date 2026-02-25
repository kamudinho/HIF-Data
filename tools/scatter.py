import streamlit as st
import plotly.express as px
import pandas as pd
from data.data_load import get_team_colors

# --- 2. FARVER & KONSTANTER ---
hif_rod = "#df003b"

def build_scatter_plot(df_plot, x_label, y_label):
    colors_dict = get_team_colors()
    
    fig = px.scatter(
        df_plot, 
        x='X_PER_GAME', 
        y='Y_PER_GAME',
        hover_name='TEAMNAME',
        text='TEAMNAME', 
        color='TEAMNAME',
        color_discrete_map=colors_dict,
        height=700,
        template="plotly_white"
    )

    # Vender Y-aksen hvis det er en "IMOD/MOD" kategori
    if any(word in y_label.upper() for word in ["MOD", "IMOD", "CONCEDED", "AGAINST"]):
        fig.update_yaxes(autorange="reversed")
    else:
        fig.update_yaxes(autorange=True)
    
    # --- HOVER-BOKS: Præcis som ønsket ---
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

    # --- AKSER: Viser kun kategorinavnet ---
    fig.update_layout(
        showlegend=False,
        xaxis=dict(title=dict(text=x_label, font=dict(size=14, color="black"))),
        yaxis=dict(title=dict(text=y_label, font=dict(size=14, color="black"))),
        margin=dict(l=50, r=50, t=50, b=50)
    )

    # Gennemsnitslinjer
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
    
    try:
        from data.season_show import SEASONNAME
        current_season = str(SEASONNAME).strip()
    except:
        current_season = "2025/2026"

    s_col = next((c for c in df_s.columns if 'SEASON' in c), None)
    if not s_col:
        st.error("Kunne ikke finde sæson-kolonne.")
        return

    df_current = df_s[df_s[s_col].astype(str).str.strip() == current_season].copy()

    # 2. Definition af Metrics (Menu-navn: Kolonne_X, Kolonne_Y, Label_X, Label_Y)
    metric_options = {
        "MÅL FOR vs. MÅL IMOD": ("GOALS", "CONCEDEDGOALS", "GOALS", "GOALS AGAINST"),
        "TOUCHES IN BOX vs. SKUD": ("TOUCHINBOX", "SHOTS", "TOUCHES IN BOX", "SHOTS"),
        "xG vs. MÅL FOR": ("XGSHOT", "GOALS", "xG", "GOALS"),
        "SKUD FOR vs. SKUD MOD": ("SHOTS", "SHOTSAGAINST", "SHOTS", "SHOTS AGAINST")
    }

    # 3. UI / Branding
    st.markdown(f"""
        <div style="background-color:{hif_rod}; padding:10px; border-radius:4px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; text-transform:uppercase; letter-spacing:1px; font-size:1.1rem;">SCATTERPLOTS</h3>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        leagues = sorted(df_current['COMPETITIONNAME'].unique()) if 'COMPETITIONNAME' in df_current.columns else []
        valgt_league = st.selectbox("Vælg Turnering", leagues)
    with c2:
        metric_type = st.selectbox("Vælg Analyse", list(metric_options.keys()))

    # 4. Filtrering og Beregning
    df_filtered = df_current[df_current['COMPETITIONNAME'] == valgt_league].copy()
    
    if not df_filtered.empty:
        x_raw, y_raw, label_x, label_y = metric_options[metric_type]
        
        for col in [x_raw, y_raw, 'MATCHES']:
            if col not in df_filtered.columns:
                df_filtered[col] = 0
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce').fillna(0)

        df_filtered['X_PER_GAME'] = df_filtered[x_raw] / df_filtered['MATCHES'].replace(0, 1)
        df_filtered['Y_PER_GAME'] = df_filtered[y_raw] / df_filtered['MATCHES'].replace(0, 1)

        # 5. Generer og vis plot
        fig = build_scatter_plot(df_filtered, label_x, label_y)
        st.plotly_chart(fig, use_container_width=True)
