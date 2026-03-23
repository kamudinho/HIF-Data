import streamlit as st

def vis_log():
    st.write("### Test af Admin Side")
    
    if "GITHUB_TOKEN" in st.secrets:
        st.success("✅ Appen kan se din GITHUB_TOKEN i Secrets")
        # Vis de første 4 tegn for at bekræfte det er den rigtige (uden at afsløre den)
        token_start = st.secrets["GITHUB_TOKEN"][:4]
        st.write(f"Token starter med: {token_start}...")
    else:
        st.error("❌ Appen kan IKKE finde GITHUB_TOKEN i dine Secrets!")
