import streamlit as st
import pandas as pd

# --- SIDETITEL ---
st.markdown('<div style="font-size: 22px; font-weight: 700; color: #1a1a1a; margin-bottom: 20px;">Modstanderanalyse & Scouting</div>', unsafe_allow_html=True)

# --- 1. VÆLG MODSTANDER ---
col_select, col_info = st.columns([2, 2])
with col_select:
    valgt_modstander = st.selectbox(
        "Vælg modstanderhold",
        ["Odense Boldklub", "AC Horsens", "Esbjerg fB", "Vendsyssel FF", "Kolding IF", "FC Fredericia"]
    )

st.divider()

# --- 2. SAMMENLIGNING AF NØGLETAL (HVIDOVRE VS MODSTANDER) ---
st.markdown(f"#### Sammenligning: Hvidovre IF vs. {valgt_modstander}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="xG For (Snit)", value="1.65", delta="HIF: 1.65 | Mod: 1.45")
with col2:
    st.metric(label="xG Imod (Snit)", value="1.10", delta="HIF: 1.10 | Mod: 1.25")
with col3:
    st.metric(label="Boldbesiddelse", value="52.4%", delta="HIF: 52% | Mod: 48%")
with col4:
    st.metric(label="PPDA (Pres)", value="9.4", delta="HIF: 9.4 | Mod: 11.2")

st.divider()

# --- 3. TAKTISK PROFIL OG SCENARIER ---
col_left, col_right = st.columns(2)

with col_left:
    st.markdown(f"#### {valgt_modstander} - Taktiske Tendenser")
    tactical_data = pd.DataFrame({
        "Parameter": [
            "Foretrukken opstilling",
            "Opbygningsfase",
            "Presspil",
            "Dødboldsrisiko (Ofte scoret imod)",
            "Omstillingsstyrke"
        ],
        "Vurdering": [
            "4-3-3",
            "Kort pasningsspil fra målmand",
            "Aggressivt mellempres",
            "Høj (Fjerneste stolpe)",
            "Middel / Hurtige wingers"
        ]
    })
    st.dataframe(tactical_data, use_container_width=True, hide_index=True)

with col_right:
    st.markdown("#### Fokusområder & Matchup-nøgler")
    st.markdown("""
    <div style="font-size: 13px; color: #333; line-height: 1.6;">
        <b>1. Udnyttelse af rum i genpres:</b><br>
        Modstanderen efterlader ofte store rum centralt, når deres centrale midtbane skubber frem i presset.<br><br>
        <b>2. Dødboldsforsvar:</b><br>
        De er sårbare over for indlæg mod bagerste stolpe i defensiv standardsituationer.<br><br>
        <b>3. Kontrol med første pres:</b><br>
        Vigtigt at bryde deres første pres-linje hurtigt for at skabe overtal på deres halvdel.
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 4. INDBYRDES OPGØR ---
st.markdown(f"#### Seneste indbyrdes opgør mod {valgt_modstander}")
h2h_data = pd.DataFrame({
    "Dato": ["12.04.2026", "22.11.2025", "14.09.2025"],
    "Kamp": [f"Hvidovre - {valgt_modstander}", f"{valgt_modstander} - Hvidovre", f"Hvidovre - {valgt_modstander}"],
    "Resultat": ["2 - 1", "1 - 1", "2 - 0"],
    "Turnering": ["NordicBet Liga", "NordicBet Liga", "NordicBet Liga"]
})
st.dataframe(h2h_data, use_container_width=True, hide_index=True)
