import streamlit as st
import pandas as pd
import google.generativeai as genai
import os


try:

    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:

    API_KEY = "PUNE_CHEIA_AICI_DOAR_PENTRU_TEST_LOCAL"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

st.title("🤖 AI Business Consultant")
st.write("Încarcă fișierul de vânzări (CSV sau Excel) și lasă AI-ul să găsească problemele.")

uploaded_file = st.file_uploader("Alege fișierul", type=['csv', 'xlsx'])

if uploaded_file is not None:
    try:

        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.success("Fișier încărcat cu succes!")

        with st.expander("👀 Vezi datele brute"):
            st.dataframe(df.head())

        st.subheader("📊 Analiză Grafică")
        st.write("Alege ce vrei să analizezi:")
        
        col1, col2 = st.columns(2)
        
        all_columns = df.columns.tolist()
        numerice = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        

        with col1:
            xa_axis = st.selectbox("Axa X (Timp/Categorie):", all_columns)
        
        with col2:
            if numerice:
                ya_axis = st.selectbox("Axa Y (Valoare):", numerice)
            else:
                st.warning("Nu am găsit coloane cu numere!")
                ya_axis = None

        if ya_axis:
            st.area_chart(df.set_index(xa_axis)[ya_axis])

        st.divider()

        st.subheader("🧠 Consultantul Virtual")
        
        if st.button("Generează Raport Detaliat"):
            if not ya_axis:
                st.error("Trebuie să selectezi o coloană numerică pentru analiză!")
            else:
                with st.spinner('AI-ul analizează relația dintre coloane...'):
                    
     
                    prompt = f"""
                    Actionează ca un Business Analyst Senior.
                    Analizează datele următoare dintr-un fișier de business.
                    
                    Utilizatorul este interesat specific de relația dintre:
                    - Axa X (Timp/Categorie): {xa_axis}
                    - Axa Y (Valoare): {ya_axis}
                    
                    Statistici sumare pentru coloana {ya_axis}:
                    {df[ya_axis].describe().to_string()}
                    
                    Te rog să generezi un raport care să conțină:
                    1. O interpretare a trendului (crește, scade, e constant?).
                    2. Identificarea oricăror anomalii (valori extreme).
                    3. Două recomandări strategice clare pentru a îmbunătăți {ya_axis}.
                    
                    Răspunsul trebuie să fie formatat frumos (Markdown), în limba Română.
                    """
                    
      
                    response = model.generate_content(prompt)
                    report_text = response.text
                    
       
                    st.markdown(report_text)
                    
        
                    st.download_button(
                        label="📥 Descarcă Raportul (TXT)",
                        data=report_text,
                        file_name="Raport_Business_AI.txt",
                        mime="text/plain"
                    )

    except Exception as e:
        st.error(f"Eroare la procesarea fișierului: {e}")
