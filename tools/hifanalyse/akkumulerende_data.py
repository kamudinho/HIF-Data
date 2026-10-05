# HIF-Data/tools/hifanalyse/akkumulerende_data.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

def plot_accumulating_timeline(df_match, team_name, category):
    """
    Genererer en akkumulerende graf over tid for et givent hold og kategori.
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Sorter hændelser efter tidspunkt
    df_sorted = df_match.sort_values("EVENT_TIMESTAMP").copy() if "EVENT_TIMESTAMP" in df_match.columns else df_match.copy()
    
    if "EVENT_MINUTE" in df_sorted.columns:
        df_sorted["MINUT"] = df_sorted["EVENT_MINUTE"]
    else:
        df_sorted["MINUT"] = range(1, len(df_sorted) + 1)

    is_against = "Imod" in category
    is_xg = "xG" in category
    is_goal = "Mål" in category

    if is_against:
        df_data = df_sorted[df_sorted["KLUB_NAVN"] != team_name]
    else:
        df_data = df_sorted[df_sorted["KLUB_NAVN"] == team_name]

    if is_xg:
        df_data["VAL"] = df_data["XG"] if "XG" in df_data.columns else df_data["XG_RAW"]
    elif is_goal:
        df_data["VAL"] = (df_data["EVENT_TYPEID"] == 16).astype(int)
    else:
        df_data["VAL"] = 1

    df_data = df_data.sort_values("MINUT")
    df_data["ACC_VAL"] = df_data["VAL"].cumsum()

    if not df_data.empty:
        ax.step(df_data["MINUT"], df_data["ACC_VAL"], where="post", linewidth=2.5, label=category, color="#e57373" if is_against else "#81c784")
        ax.fill_between(df_data["MINUT"], df_data["ACC_VAL"], step="post", alpha=0.2, color="#e57373" if is_against else "#81c784")

    ax.set_title(f"Akkumuleret {category} - {team_name}", fontsize=14, fontweight="bold", color="white", pad=15)
    ax.set_xlabel("Kampens minutter", fontsize=11, color="white")
    ax.set_ylabel("Akkumuleret værdi", fontsize=11, color="white")
    
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")
    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    for spine in ax.spines.values():
        spine.set_edgecolor("white")

    ax.grid(True, linestyle="--", alpha=0.3)
    
    return fig


def vis_side(df_all=None, t_sel=None):
    """
    Hovedfunktion der kaldes af appen for at vise siden.
    Understøtter både direkte kald uden argumenter og kald fra andre sider.
    """
    st.markdown("### Akkumuleret Udvikling i Kampen")
    st.caption("Følg udviklingen af xG, mål, afslutninger og skud imod minut for minut.")

    # Hvis modulet kaldes uden argumenter, henter vi fra session state eller standard værdier
    if df_all is None:
        df_all = st.session_state.get("df_all", pd.DataFrame())
    if t_sel is None:
        t_sel = st.session_state.get("t_sel", "Hvidovre")

    if df_all.empty:
        st.info("Ingen data tilgængelig. Indlæs venligst data først.")
        return

    # Layout: Graf til venstre (eller stor del), dropdown-indstillinger i højre kolonne
    col_graf, col_filter = st.columns([3, 1])

    with col_filter:
        st.markdown("##### Indstillinger")
        
        # 1. Dropdown for valg af hold i højre hjørne
        hold_muligheder = [t_sel, "Modstander (Samlet)"]
        valgte_hold = st.selectbox("Vælg hold", hold_muligheder, key="acc_hold_sel")
        
        # 2. Dropdown for valg af kategori i højre hjørne
        kategorier = [
            "xG (For)", 
            "Mål (For)", 
            "Afslutninger (For)", 
            "xG (Imod)", 
            "Skud (Imod)"
        ]
        valgt_kategori = st.selectbox("Vælg kategori", kategorier, key="acc_kat_sel")

    with col_graf:
        df_team = df_all[df_all["KLUB_NAVN"] == t_sel] if "KLUB_NAVN" in df_all.columns else df_all

        if not df_team.empty:
            # Generer figur
            fig = plot_accumulating_timeline(df_team, valgte_hold if valgte_hold != "Modstander (Samlet)" else f"Modstander (vs {t_sel})", valgt_kategori)
            
            # Gem til bytes for visning og download
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=300, bbox_inches='tight')
            buf.seek(0)
            img_bytes = buf.getvalue()
            plt.close(fig)

            # Vis som billede i Streamlit
            st.image(img_bytes, use_container_width=True)

            # Download-knap til billedet
            st.download_button(
                label="📸 Download akkumuleret graf som billede",
                data=img_bytes,
                file_name=f"akkumuleret_{valgt_kategori.lower().replace(' ', '_')}.png",
                mime="image/png"
            )
        else:
            st.info("Ingen data tilgængelig for det valgte hold.")

if __name__ == "__main__":
    vis_side()
