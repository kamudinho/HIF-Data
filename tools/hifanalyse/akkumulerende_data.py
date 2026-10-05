import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

def plot_accumulating_timeline(df_match, team_name, category):
    """
    Genererer en akkumulerende graf over tid for et givent hold og kategori.
    Kategorier kan f.eks. være: 'xG (For)', 'Mål (For)', 'Afslutninger (For)', 'xG (Imod)', 'Skud (Imod)'
    """
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Sorter hændelser efter tidspunkt
    df_sorted = df_match.sort_values("EVENT_TIMESTAMP").copy()
    
    # Konverter timestamp til minutter inde i kampen (antager standard 0-90+ minutter)
    # Hvis du har en 'MINUTE'-kolonne i din data, kan du bruge den direkte. Ellers estimerer vi ud fra timestamp eller rækkefølge.
    if "EVENT_MINUTE" in df_sorted.columns:
        df_sorted["MINUT"] = df_sorted["EVENT_MINUTE"]
    else:
        # Fallback hvis minut ikke findes direkte (fx sekvens-index eller dummy-minut)
        df_sorted["MINUT"] = range(1, len(df_sorted) + 1)

    # Logik baseret på valgt kategori
    is_against = "Imod" in category
    is_xg = "xG" in category
    is_goal = "Mål" in category

    # Filtrer data afhængigt af om det er for holdet eller imod holdet
    if is_against:
        # Hændelser mod holdet (hvor holdet IKKE er event-ejer/konstant)
        df_data = df_sorted[df_sorted["KLUB_NAVN"] != team_name]
    else:
        # Hændelser for holdet
        df_data = df_sorted[df_sorted["KLUB_NAVN"] == team_name]

    if is_xg:
        df_data["VAL"] = df_data["XG"] if "XG" in df_data.columns else df_data["XG_RAW"]
    elif is_goal:
        df_data["VAL"] = (df_data["EVENT_TYPEID"] == 16).astype(int)
    else:
        # Generelle afslutninger/skud
        df_data["VAL"] = 1

    # Lav akkumuleret sum over tid
    df_data = df_data.sort_values("MINUT")
    df_data["ACC_VAL"] = df_data["VAL"].cumsum()

    # Plot grafen
    if not df_data.empty:
        ax.step(df_data["MINUT"], df_data["ACC_VAL"], where="post", linewidth=2.5, label=category)
        ax.fill_between(df_data["MINUT"], df_data["ACC_VAL"], step="post", alpha=0.2)

    ax.set_title(f"Akkumuleret {category} - {team_name}", fontsize=14, fontweight="bold", color="white")
    ax.set_xlabel("Kampens minutter", fontsize=11, color="white")
    ax.set_ylabel("Akkumuleret værdi", fontsize=11, color="white")
    
    # Styling af mørkt tema (tilpasset Streamlit standard dark mode)
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#0e1117")
    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    for spine in ax.spines.values():
        spine.set_edgecolor("white")

    ax.grid(True, linestyle="--", alpha=0.3)
    
    return fig
