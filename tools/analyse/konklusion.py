import streamlit as st

def vis_side():
    # --- STYLING AF KONKLUSIONSTEKST ---
    st.markdown("""
        <style>
            .conclusion-text { 
                color: #df003b; 
                font-weight: bold; 
                margin-top: 10px; 
            }
            .section-title {
                font-weight: bold;
                font-size: 1.1rem;
                margin-bottom: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- TOP SEKTION MED TITEL OG DROPDOWN TIL HØJRE ---
    col_titel, col_spacer, col_drop = st.columns([2, 1, 1])
    
    with col_titel:
        st.markdown("## Performance Analyse")
    
    with col_drop:
        valgt_hold = st.selectbox("Vælg hold:", ["Hvidovre", "OB", "FC Fredericia"], label_visibility="collapsed")

    # --- HARDKODET DATA (OVERSAT) ---
    hold_data = {
        "Hvidovre": {
            "attack": [
                "**Nr. 8** for antal mål scoret totalt (63)",
                "**Nr. 15** for mål scoret i åbent spil (25)",
                "10 færre mål scoret end xG skabt",
                "Topscorer: **Ben Knight (10)**"
            ],
            "attack_conc": "begrænset af manglende skarphed i afslutningerne",
            "chance": [
                "**Nr. 1** for xG pr. afslutning (0.14)",
                "**Nr. 24** for andel af afslutninger uden for feltet (27%)",
                "**Nr. 18** for gennembrud fra sidste tredjedel til feltet (16%)"
            ],
            "chance_conc": "prioriterer chancer af høj kvalitet, men har svært ved at komme ind i feltet",
            "build": [
                "**Nr. 8** højeste gennemsnitlige boldbesiddelse (51.3%)",
                "**Nr. 4** højeste antal aktioner på modstanderens tredjedel (65%)",
                "**Nr. 8** for andel af lange bolde (23%)"
            ],
            "build_conc": "stærk i boldomgangen og foretrækker et mere direkte spil"
        },
        "OB": {
            "attack": [
                "**Nr. 1** for antal mål scoret totalt (78)",
                "**Nr. 1** for mål scoret i åbent spil (42)",
                "5 flere mål scoret end xG skabt",
                "Topscorer: **Luca Kjerrumgaard (15)**"
            ],
            "attack_conc": "kyniske afslutninger og stor volumen af chancer",
            "chance": [
                "**Nr. 3** for xG pr. afslutning (0.12)",
                "**Nr. 5** for andel af afslutninger uden for feltet (18%)",
                "**Nr. 2** for gennembrud fra sidste tredjedel til feltet (22%)"
            ],
            "chance_conc": "fremragende til at bryde ind i feltet og skabe store chancer",
            "build": [
                "**Nr. 1** højeste gennemsnitlige boldbesiddelse (58.2%)",
                "**Nr. 1** højeste antal aktioner på modstanderens tredjedel (72%)",
                "**Nr. 22** for andel af lange bolde (12%)"
            ],
            "build_conc": "dominerende besiddelsesbaseret stil med korte kombinationer"
        },
        "FC Fredericia": {
            "attack": [
                "**Nr. 4** for antal mål scoret totalt (55)",
                "**Nr. 6** for mål scoret i åbent spil (31)",
                "2 færre mål scoret end xG skabt",
                "Topscorer: **Asbjørn Bøndergaard (12)**"
            ],
            "attack_conc": "stabil produktion der matcher de underliggende præstationer",
            "chance": [
                "**Nr. 10** for xG pr. afslutning (0.10)",
                "**Nr. 12** for andel af afslutninger uden for feltet (22%)",
                "**Nr. 8** for gennembrud fra sidste tredjedel til feltet (19%)"
            ],
            "chance_conc": "balanceret tilgang til chanceproduktion",
            "build": [
                "**Nr. 3** højeste gennemsnitlige boldbesiddelse (54.1%)",
                "**Nr. 5** højeste antal aktioner på modstanderens tredjedel (63%)",
                "**Nr. 15** for andel af lange bolde (18%)"
            ],
            "build_conc": "kontrolleret opbygningsspil med fokus på central fremdrift"
        }
    }

    data = hold_data[valgt_hold]

    # --- GRID LAYOUT (2 BOKSE PR. RÆKKE) ---

    # Række 1
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        with st.container(border=True):
            st.markdown('<p class="section-title">Angreb & Output:</p>', unsafe_allow_html=True)
            for line in data["attack"]:
                st.markdown(f"• {line}")
            st.markdown(f'<p class="conclusion-text">Konklusion – {data["attack_conc"]}</p>', unsafe_allow_html=True)

    with row1_col2:
        with st.container(border=True):
            st.markdown('<p class="section-title">Chanceskabelse:</p>', unsafe_allow_html=True)
            for line in data["chance"]:
                st.markdown(f"• {line}")
            st.markdown(f'<p class="conclusion-text">Konklusion – {data["chance_conc"]}</p>', unsafe_allow_html=True)

    # Række 2
    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        with st.container(border=True):
            st.markdown('<p class="section-title">Opbygningsspil:</p>', unsafe_allow_html=True)
            for line in data["build"]:
                st.markdown(f"• {line}")
            st.markdown(f'<p class="conclusion-text">Konklusion – {data["build_conc"]}</p>', unsafe_allow_html=True)

    with row2_col2:
        st.empty()

if __name__ == "__main__":
    vis_side()
