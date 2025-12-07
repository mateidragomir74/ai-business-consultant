import streamlit as st
import xml.etree.ElementTree as ET
import google.generativeai as genai

# 1. CONFIGURARE PAGINA
st.set_page_config(page_title="Auditor e-Factura", page_icon="🛡️")

# 2. SECURITATE CHEIE
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
except:
    API_KEY = "PUNE_CHEIA_AICI_LOCAL"

genai.configure(api_key=API_KEY)

# --- ZONA DE DIAGNOSTIC (Sidebar) ---
st.sidebar.header("🔧 Diagnostic Server")
try:
    # Verificam versiunea bibliotecii
    st.sidebar.write(f"Versiune Library: `{genai.__version__}`")
    
    # Intrebam Google ce modele avem voie sa folosim
    st.sidebar.write("Caut modele disponibile...")
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
    
    st.sidebar.success(f"Găsit: {len(available_models)} modele")
    with st.sidebar.expander("Vezi lista completă"):
        st.write(available_models)

except Exception as e:
    st.sidebar.error(f"Eroare critică la conectare: {e}")
    available_models = []

# --- SELECTIA AUTOMATA A MODELULUI ---
# Incercam sa gasim cel mai bun model disponibil in lista
model_name = None

# Lista de prioritati (ce vrem sa folosim)
prioritati = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-1.5-flash-001', 'models/gemini-pro']

for candidat in prioritati:
    if candidat in available_models:
        model_name = candidat
        break

if model_name:
    st.sidebar.info(f"✅ Folosim modelul: `{model_name}`")
    model = genai.GenerativeModel(model_name)
else:
    st.error("❌ EROARE FATALĂ: Nu am găsit niciun model compatibil pe acest cont Google.")
    st.stop() # Oprim aplicatia aici daca nu avem model

# --- 3. LOGICA DE VALIDARE (PARSER XML) ---
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
            "linii_factura": [] 
        }

        for linie in root.findall('.//cac:InvoiceLine', ns):
            nume_produs = linie.find('.//cac:Item/cbc:Name', ns).text
            pret = linie.find('.//cbc:LineExtensionAmount', ns).text
            data["linii_factura"].append(f"- {nume_produs}: {pret} RON")

        return data

    except Exception as e:
        return {"eroare": str(e)}

# 4. INTERFATA VIZUALA
st.title("🛡️ Auditor Digital e-Factura")

fisier = st.file_uploader("Încarcă fișierul XML (UBL 2.1)", type=["xml"])

if fisier:
    rezultat = analizeaza_xml(fisier)

    if "eroare" in rezultat:
        st.error(f"Eroare XML: {rezultat['eroare']}")
    else:
        col1, col2 = st.columns(2)
        col1.info(f"📤 **Furnizor:** {rezultat['furnizor']}")
        col2.info(f"📥 **Client:** {rezultat['client']}")

        st.divider()

        st.subheader("1. Verificare Matematică")
        c1, c2, c3 = st.columns(3)
        c1.metric("Subtotal", f"{rezultat['subtotal']:.2f} RON")
        c2.metric("Total Calculat", f"{rezultat['total_calculat']:.2f} RON")
        c3.metric("Total Cerut", f"{rezultat['total_de_plata']:.2f} RON")

        diferenta = rezultat['total_de_plata'] - rezultat['total_calculat']

        if abs(diferenta) > 0.01:
            st.error(f"❌ ALERTĂ: Diferență: {diferenta:.2f} RON")
        else:
            st.success("✅ Matematic Corect.")

        st.divider()

        st.subheader("2. Audit Fiscal (AI)")
        
        if st.button("Scanează Riscuri"):
            with st.spinner(f"Analizez cu {model_name}..."):
                try:
                    prompt = f"""
                    Analizează factura de la {rezultat['furnizor']}.
                    Produse: {rezultat['linii_factura']}
                    Ești auditor fiscal.
                    1. Sunt descrierile clare?
                    2. Riscuri?
                    3. Verdict: MIC/MEDIU/MARE.
                    Răspunde scurt în Română.
                    """
                    response = model.generate_content(prompt)
                    st.write(response.text)

                except Exception as e:
                    st.error(f"Eroare AI: {e}")
