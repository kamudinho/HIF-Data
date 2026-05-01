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
            /* Gør overskrifterne i boksene lidt mindre og skarpe */
            .section-title {
                font-weight: bold;
                font-size: 1.1rem;
                margin-bottom: 10px;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- TOP SEKTION MED TITEL OG DROPDOWN TIL HØJRE ---
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("## Performance Analysis")
    
    with col2:
        # Flytter dropdown op til højre
        valgt_hold = st.selectbox("Vælg hold:", ["Hvidovre", "OB", "FC Fredericia"], label_visibility="collapsed")

    # --- HARDKODET DATA ---
    hold_data = {
        "Hvidovre": {
            "attack": [
                "**8th** for total goals scored (63)",
                "**15th** for open-play goals (25)",
                "10 fewer goals scored than xG created",
                "Highest goalscorer: **Ben Knight (10)**"
            ],
            "attack_conc": "limited by poor quality finishing",
            "chance": [
                "**1st** for xG per shot (0.14)",
                "**24th** for percentage of shots taken outside the box (27%)",
                "**18th** for final-third to box entries (16%)"
            ],
            "chance_conc": "prefer high quality chances, but struggle to get into the box",
            "build": [
                "**8th** highest average possession (51.3%)",
                "**4th** highest possessions to final third (65%)",
                "**8th** for long ball percentage (23%)"
            ],
            "build_conc": "strong passing retention and favour a more direct game"
        },
        "OB": {
            "attack": [
                "**1st** for total goals scored (78)",
                "**1st** for open-play goals (42)",
                "5 more goals scored than xG created",
                "Highest goalscorer: **Luca Kjerrumgaard (15)**"
            ],
            "attack_conc": "clinical finishing and high volume of chances",
            "chance": [
                "**3rd** for xG per shot (0.12)",
                "**5th** for percentage of shots taken outside the box (18%)",
                "**2nd** for final-third to box entries (22%)"
            ],
            "chance_conc": "excellent at breaking into the box and creating big chances",
            "build": [
                "**1st** highest average possession (58.2%)",
                "**1st** highest possessions to final third (72%)",
                "**22nd** for long ball percentage (12%)"
            ],
            "build_conc": "dominant possession-based style with short combinations"
        },
        "FC Fredericia": {
            "attack": [
                "**4th** for total goals scored (55)",
                "**6th** for open-play goals (31)",
                "2 fewer goals scored than xG created",
                "Highest goalscorer: **Asbjørn Bøndergaard (12)**"
            ],
            "attack_conc": "steady output matching the underlying performance",
            "chance": [
                "**10th** for xG per shot (0.10)",
                "**12th** for percentage of shots taken outside the box (22%)",
                "**8th** for final-third to box entries (19%)"
            ],
            "chance_conc": "balanced approach to chance creation",
            "build": [
                "**3rd** highest average possession (54.1%)",
                "**5th** highest possessions to final third (63%)",
                "**15th** for long ball percentage (18%)"
            ],
            "build_conc": "controlled build-up with focus on central progression"
        }
    }

    data = hold_data[valgt_hold]

    # --- RENDERING MED BORDERS ---

    # Attacking Output
    with st.container(border=True):
        st.markdown('<p class="section-title">Attacking Output:</p>', unsafe_allow_html=True)
        for line in data["attack"]:
            st.markdown(f"• {line}")
        st.markdown(f'<p class="conclusion-text">Conclusion – {data["attack_conc"]}</p>', unsafe_allow_html=True)

    st.write("") # Mellemrum

    # Chance Creation
    with st.container(border=True):
        st.markdown('<p class="section-title">Chance Creation:</p>', unsafe_allow_html=True)
        for line in data["chance"]:
            st.markdown(f"• {line}")
        st.markdown(f'<p class="conclusion-text">Conclusion – {data["chance_conc"]}</p>', unsafe_allow_html=True)

    st.write("") # Mellemrum

    # Build-Up
    with st.container(border=True):
        st.markdown('<p class="section-title">Build-Up:</p>', unsafe_allow_html=True)
        for line in data["build"]:
            st.markdown(f"• {line}")
        st.markdown(f'<p class="conclusion-text">Conclusion – {data["build_conc"]}</p>', unsafe_allow_html=True)

if __name__ == "__main__":
    vis_side()
