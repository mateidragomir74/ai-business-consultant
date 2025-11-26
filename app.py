import streamlit as st
import pandas as pd
import google.generativeai as genai

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "PUNE_CHEIA_AICI_DOAR_PENTRU_TEST_LOCAL"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')
st.title("🤖 AI Business Consultant")
st.write("Încarcă fișierul de vânzări (CSV sau Excel) și lasă AI-ul să găsească problemele.")
uploaded_file = st.file_uploader("vanzari_fictive.xslx", type=['csv', 'xlsx'])
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        st.success("Fișier încărcat cu succes!")
        st.subheader("Previzualizare Date:")
        st.dataframe(df.head())
        descriere_date = df.describe().to_string()
        coloane = list(df.columns)
        st.write("Analizăm structura datelor...")
        if st.button("Generează Raport AI"):
            with st.spinner('AI-ul analizează cifrele...'):
                #
                prompt = f"""
                Ești un consultant de business expert. 
                Analizează următoarele date statistice ale unui set de date de vânzări/business.

                Coloanele disponibile sunt: {coloane}

                Statistici sumare (descriere matematică):
                {descriere_date}

                Sarcina ta:
                1. Identifică trenduri sau anomalii evidente din aceste cifre.
                2. Oferă 3 sfaturi acționabile pentru patronul afacerii, bazat strict pe aceste cifre.
                3. Scrie în limba Română, ton profesional dar direct.
                """

                response = model.generate_content(prompt)

                st.subheader("📝 Raportul Consultantului AI")
                st.markdown(response.text)

        st.subheader("📊 Analiză Grafică")
        col1, col2 = st.columns(2) # Facem doua coloane vizuale pe site
        all_columns = df.columns.tolist()
        numerice = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        with col1:
            xa_axis = st.selectbox("Alege axa X (Timp/Nume):", all_columns)
        with col2:
            ya_axis = st.selectbox("Alege axa Y (Valoare):", numerice)
        if st.button("Generează Grafic"):
            chart_data = df.set_index(xa_axis)
            st.area_chart(chart_data[ya_axis])

            st.info(f"Graficul arată evoluția **{ya_axis}** în funcție de **{xa_axis}**.")

    except Exception as e:
        st.error(f"A apărut o eroare la citirea fișierului: {e}")