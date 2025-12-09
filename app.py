import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from io import BytesIO

# --- CONFIGURARE PAGINĂ ---
st.set_page_config(page_title="Auditor e-Factura", page_icon="🧾", layout="wide")

st.title("🧾 Auditor e-Factura (RO)")
st.markdown("Verificare structură XML și corectitudine calcule (ANAF UBL 2.1)")

# --- LOGICĂ DE PARSARE XML (E-FACTURA SPECIFIC) ---
def parse_invoice_xml(file_content):
    try:
        tree = ET.parse(file_content)
        root = tree.getroot()

        # Namespace-urile UBL sunt complicate, de multe ori e mai sigur să le ignorăm
        # sau să folosim un map, dar pentru robustețe vom curăța tag-urile la căutare
        # sau vom folosi un dictionar de namespaces standard.
        ns = {
            'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            'inv': "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
        }

        # Helper pentru a extrage text sigur
        def get_text(element, path, namespaces=ns):
            node = element.find(path, namespaces)
            return node.text if node is not None else "N/A"

        # 1. HEADER FACTURĂ
        invoice_data = {
            "ID Factura": get_text(root, "cbc:ID"),
            "Data Emitere": get_text(root, "cbc:IssueDate"),
            "Tip Factura": get_text(root, "cbc:InvoiceTypeCode"),
            "Moneda": get_text(root, "cbc:DocumentCurrencyCode")
        }

        # 2. FURNIZOR (AccountingSupplierParty)
        supplier = root.find("cac:AccountingSupplierParty/cac:Party", ns)
        if supplier:
            invoice_data["Nume Furnizor"] = get_text(supplier, "cac:PartyLegalEntity/cbc:RegistrationName", ns)
            invoice_data["CUI Furnizor"] = get_text(supplier, "cac:PartyTaxScheme/cbc:CompanyID", ns)

        # 3. CLIENT (AccountingCustomerParty)
        customer = root.find("cac:AccountingCustomerParty/cac:Party", ns)
        if customer:
            invoice_data["Nume Client"] = get_text(customer, "cac:PartyLegalEntity/cbc:RegistrationName", ns)
            invoice_data["CUI Client"] = get_text(customer, "cac:PartyTaxScheme/cbc:CompanyID", ns)

        # 4. TOTALURI (TaxTotal & LegalMonetaryTotal)
        # Atenție: Pot fi mai multe tag-uri TaxTotal (unul pe factură, unul pe linie în unele cazuri rare, dar standardul RO are unul principal)
        tax_total = root.find("cac:TaxTotal", ns)
        if tax_total:
            invoice_data["Total TVA (XML)"] = float(get_text(tax_total, "cbc:TaxAmount", ns) or 0)
        
        monetary_total = root.find("cac:LegalMonetaryTotal", ns)
        if monetary_total:
            invoice_data["Total Net (XML)"] = float(get_text(monetary_total, "cbc:TaxExclusiveAmount", ns) or 0)
            invoice_data["Total Brut (XML)"] = float(get_text(monetary_total, "cbc:PayableAmount", ns) or 0)

        return invoice_data, root, ns

    except ET.ParseError:
        return None, None, None
    except Exception as e:
        return None, str(e), None

# --- UI ÎNCĂRCARE ---
uploaded_file = st.file_uploader("Încarcă fișierul XML (e-Factura)", type=["xml"])

if uploaded_file:
    # Citim fișierul
    data, root_element, namespaces = parse_invoice_xml(uploaded_file)

    if data and root_element:
        st.success("XML validat structural (Well-formed)")
        
        # AFIȘARE SUMAR
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("🏢 **Furnizor**")
            st.write(f"**{data.get('Nume Furnizor')}**")
            st.write(f"CUI: {data.get('CUI Furnizor')}")
        
        with col2:
            st.info("👤 **Client**")
            st.write(f"**{data.get('Nume Client')}**")
            st.write(f"CUI: {data.get('CUI Client')}")

        with col3:
            st.info("💰 **Detalii Plată**")
            st.write(f"ID: {data.get('ID Factura')}")
            st.metric("Total de Plată", f"{data.get('Total Brut (XML)')} {data.get('Moneda')}")

        st.divider()

        # --- AUDIT DE CALCUL (SIMPLIFICAT) ---
        st.subheader("🔍 Audit Calcule & Linii")
        
        # Extragem liniile pentru a recalcula
        lines = []
        calculated_net = 0.0
        calculated_vat = 0.0

        invoice_lines = root_element.findall("cac:InvoiceLine", namespaces)
        
        for line in invoice_lines:
            line_id = line.find("cbc:ID", namespaces).text
            # Cantitate
            qty = float(line.find("cbc:InvoicedQuantity", namespaces).text or 0)
            # Preț Unitar
            price_node = line.find("cac:Price/cbc:PriceAmount", namespaces)
            unit_price = float(price_node.text or 0)
            
            # Valoare Netă Linie (LineExtensionAmount)
            line_net_xml = float(line.find("cbc:LineExtensionAmount", namespaces).text or 0)
            
            # Recalculare Net
            recalc_net = round(qty * unit_price, 2)
            
            # Cota TVA
            tax_category = line.find("cac:Item/cac:ClassifiedTaxCategory", namespaces)
            vat_percent = float(tax_category.find("cbc:Percent", namespaces).text or 0)
            
            # Recalculare TVA
            recalc_vat = round(line_net_xml * (vat_percent / 100), 2)

            calculated_net += line_net_xml
            calculated_vat += recalc_vat

            lines.append({
                "Linie": line_id,
                "Cantitate": qty,
                "Preț Unitar": unit_price,
                "Net (XML)": line_net_xml,
                "Net (Recalculat)": recalc_net,
                "TVA %": vat_percent,
                "TVA (Estimat)": recalc_vat
            })

        # Afișare tabel linii
        df_lines = pd.DataFrame(lines)
        st.dataframe(df_lines, use_container_width=True)

        # --- REZULTAT AUDIT ---
        st.subheader("Rezultat Audit")
        
        col_aud1, col_aud2 = st.columns(2)
        
        diff_net = abs(data.get('Total Net (XML)') - calculated_net)
        diff_vat = abs(data.get('Total TVA (XML)') - calculated_vat)

        with col_aud1:
            st.write("### Verificare Net")
            st.write(f"XML: {data.get('Total Net (XML)')}")
            st.write(f"Calculat (sumă linii): {round(calculated_net, 2)}")
            if diff_net < 0.05: # Toleranță mică
                st.success("✅ OK")
            else:
                st.error(f"❌ Discrepanță: {round(diff_net, 2)}")

        with col_aud2:
            st.write("### Verificare TVA")
            st.write(f"XML: {data.get('Total TVA (XML)')}")
            st.write(f"Calculat (estimare): {round(calculated_vat, 2)}")
            if diff_vat < 1.0: # Toleranță mai mare la TVA din cauza rotunjirilor per linie vs global
                st.success("✅ OK (în marja de rotunjire)")
            else:
                st.warning(f"⚠️ Posibilă eroare rotunjire sau discrepanță: {round(diff_vat, 2)}")

    elif isinstance(root_element, str):
        st.error(f"Eroare la parsare: {root_element}")
    else:
        st.error("Fișierul nu pare a fi un XML e-Factura valid.")

else:
    st.info("Aștept încărcarea unui XML...")
