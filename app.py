import streamlit as st
import xml.etree.ElementTree as ET
import google.generativeai as genai


st.set_page_config(page_title="Auditor e-Factura", page_icon="🛡️")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "PUNE_CHEIA_AICI_LOCAL"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')



def analizeaza_xml(uploaded_file):
    try:
        tree = ET.parse(uploaded_file)
        root = tree.getroot()


        ns = {
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'
        }


        data = {
            "furnizor": root.find('.//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name', ns).text,
            "client": root.find('.//cac:AccountingCustomerParty/cac:Party/cac:PartyName/cbc:Name', ns).text,
            "data_emitere": root.find('cbc:IssueDate', ns).text,
            "subtotal": float(root.find('.//cac:LegalMonetaryTotal/cbc:LineExtensionAmount', ns).text),
            "total_calculat": float(root.find('.//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount', ns).text),
            "total_de_plata": float(root.find('.//cac:LegalMonetaryTotal/cbc:PayableAmount', ns).text),
            "linii_factura": []  # Vom colecta si produsele pentru AI
        }


        for linie in root.findall('.//cac:InvoiceLine', ns):
            nume_produs = linie.find('.//cac:Item/cbc:Name', ns).text
            pret = linie.find('.//cbc:LineExtensionAmount', ns).text
            data["linii_factura"].append(f"- {nume_produs}: {pret} RON")

        return data

    except Exception as e:
        return {"eroare": str(e)}



st.title("🛡️ Auditor Digital e-Factura")
st.markdown("Verifică instantaneu XML-urile ANAF pentru erori matematice și riscuri fiscale.")

fisier = st.file_uploader("Încarcă fișierul XML (UBL 2.1)", type=["xml"])

if fisier:

    rezultat = analizeaza_xml(fisier)

    if "eroare" in rezultat:
        st.error(
            f"Nu am putut citi fișierul XML. Asigură-te că e format e-Factura valid.\nEroare: {rezultat['eroare']}")
    else:

        col1, col2 = st.columns(2)
        col1.info(f"📤 **Furnizor:** {rezultat['furnizor']}")
        col2.info(f"📥 **Client:** {rezultat['client']}")

        st.divider()


        st.subheader("1. Verificare Matematică")

        c1, c2, c3 = st.columns(3)
        c1.metric("Subtotal (Fără TVA)", f"{rezultat['subtotal']:.2f} RON")
        c2.metric("Total Calculat (Corect)", f"{rezultat['total_calculat']:.2f} RON")
        c3.metric("Total Cerut (Payable)", f"{rezultat['total_de_plata']:.2f} RON")

        diferenta = rezultat['total_de_plata'] - rezultat['total_calculat']

        if abs(diferenta) > 0.01:
            st.error(f"❌ ALERTĂ: Factura are erori! Diferență: {diferenta:.2f} RON")
            st.warning("Această factură riscă să fie respinsă de contabilitate sau ANAF.")
        else:
            st.success("✅ Factura este corectă matematic.")

        st.divider()


        st.subheader("2. Audit Fiscal (AI)")

        if st.button("Scanează pentru Riscuri (Gemini)"):
            with st.spinner("AI-ul analizează conținutul facturii..."):
                prompt = f"""
                Ești un auditor fiscal expert în legislația din România.
                Analizează următoarea factură:
                Furnizor: {rezultat['furnizor']}
                Linii factură:
                {chr(10).join(rezultat['linii_factura'])}

                Sarcina ta:
                1. Analizează dacă descrierea produselor/serviciilor este suficient de clară pentru ANAF (evită descrieri vagi gen "Servicii diverse").
                2. Identifică potențiale riscuri de nedeductibilitate.
                3. Dă un verdict scurt: "RISC MIC", "RISC MEDIU" sau "RISC MARE".

                Răspunde scurt și la obiect în limba Română.
                """

                response = model.generate_content(prompt)
                st.write(response.text)
