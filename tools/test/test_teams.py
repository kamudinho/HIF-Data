import streamlit as st
import pandas as pd
import os

def super_clean(text):
    if not isinstance(text, str): return text
    rep = {
        "ƒç": "č", "ƒá": "ć", "≈°": "š", "≈æ": "ž", "√¶": "æ", "√∏": "ø", "√•": "å",
        "√Ü": "Æ", "√ò": "Ø", "√Ö": "Å", "√Å": "Á", "√©": "é", "√∂": "ö", "√º": "ü"
    }
    for wrong, right in rep.items(): text = text.replace(wrong, right)
    return text

def vis_side():
    # CSS til at style vores HTML-tabel så den ligner Streamlits
    st.markdown("""
        <style>
            .custom-table { width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; }
            .custom-table th { background-color: #f0f2f6; padding: 10px; text-align: left; border-bottom: 2px solid #ddd; }
            .custom-table td { padding: 8px; border-bottom: 1px solid #eee; }
            .custom-table tr:hover { background-color: #f9f9f9; }
            .pos { color: #28a745; font-weight: bold; }
            .neg { color: #dc3545; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""<div style="background-color:#cc0000; padding:10px; border-radius:4px; margin-bottom:20px;">
        <h3 style="color:white; margin:0; text-align:center; font-family:sans-serif; font-size:1.1rem; text-transform:uppercase;">TEST: HOLDSTATISTIK</h3>
    </div>""", unsafe_allow_html=True)
    
    csv_path = "data/testdata/teams.csv"
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding='utf-8-sig').fillna(0)
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].apply(super_clean)

        # Filtre
        ligaer = ["Alle"] + sorted([str(x) for x in df['SEASONNAME'].unique() if x != 0])
        valgt_liga = st.selectbox("Sæson / Liga", ligaer)
        if valgt_liga != "Alle": df = df[df['SEASONNAME'] == valgt_liga]

        # Faner
        tabs = st.tabs(["Angreb & xG", "Forsvar", "Overblik"])

        with tabs[0]: # Angreb & xG
            html = "<table class='custom-table'><thead><tr><th>Hold</th><th>Mål</th><th>xG (Diff)</th><th>Skud</th></tr></thead><tbody>"
            for _, r in df.iterrows():
                diff = r['GOALS'] - r['XGSHOT']
                diff_class = "pos" if diff > 0 else "neg"
                diff_str = f"<span class='{diff_class}'>({'+' if diff > 0 else ''}{diff:.2f})</span>"
                
                html += f"<tr><td>{r['TEAMNAME']}</td><td>{int(r['GOALS'])}</td><td>{r['XGSHOT']:.2f} {diff_str}</td><td>{int(r['SHOTS'])}</td></tr>"
            html += "</tbody></table>"
            st.markdown(html, unsafe_allow_html=True)

        with tabs[1]: # Forsvar
            html = "<table class='custom-table'><thead><tr><th>Hold</th><th>Mål Imod</th><th>xG Imod (Diff)</th><th>PPDA</th></tr></thead><tbody>"
            for _, r in df.iterrows():
                # For forsvar: Positiv diff (xG imod > mål) er grøn
                diff = r['XGSHOTAGAINST'] - r['CONCEDEDGOALS']
                diff_class = "pos" if diff > 0 else "neg"
                diff_str = f"<span class='{diff_class}'>({'+' if diff > 0 else ''}{diff:.2f})</span>"
                
                html += f"<tr><td>{r['TEAMNAME']}</td><td>{int(r['CONCEDEDGOALS'])}</td><td>{r['XGSHOTAGAINST']:.2f} {diff_str}</td><td>{r['PPDA']:.2f}</td></tr>"
            html += "</tbody></table>"
            st.markdown(html, unsafe_allow_html=True)

        with tabs[2]: # Overblik
            st.dataframe(df[['TEAMNAME', 'MATCHES', 'TOTALWINS', 'TOTALDRAWS', 'TOTALLOSSES', 'TOTALPOINTS']], use_container_width=True, hide_index=True)

    else:
        st.error("CSV filen kunne ikke findes.")
