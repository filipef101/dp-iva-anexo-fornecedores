import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import re
from xml.dom import minidom
import sys
import os

def extract_nif(text):
    # Extract the 9-digit NIF from strings like "123456789 - Company Name"
    match = re.match(r'(\d{9})', text)
    return match.group(1) if match else None

def get_trimester(month):
    # Convert month to trimester code
    return f"{((month-1)//3 + 1):02d}T"

def convert_euro_to_float(value):
    # Remove € symbol, spaces and convert comma to dot
    if pd.isna(value):
        return 0.0
    # Convert to float and multiply by 100 to get cents
    return float(value.replace('€', '').replace('.', '').replace(',', '.').strip()) * 100

def process_csv(csv_path):
    # Read CSV with semicolon delimiter
    df = pd.read_csv(csv_path, sep=';')
    
    print("\n=== Original Data Sample ===")
    print(df[['Data Emissão', 'Emitente', 'Base Tributável', 'IVA']].head())
    
    print("\n=== Total Before Processing ===")
    print(f"Total Base Tributável: {df['Base Tributável'].sum()}")
    print(f"Total IVA: {df['IVA'].sum()}")
    
    # Convert monetary columns
    df['Base Tributável'] = df['Base Tributável'].apply(convert_euro_to_float)
    df['IVA'] = df['IVA'].apply(convert_euro_to_float)
    
    # Convert date string to datetime
    df['Data Emissão'] = pd.to_datetime(df['Data Emissão'], format='%d/%m/%Y')
    
    # Extract year and month
    df['Year'] = df['Data Emissão'].dt.year
    df['Month'] = df['Data Emissão'].dt.month
    
    # Extract NIF from Emitente column
    df['NIF'] = df['Emitente'].apply(extract_nif)
    
    # Calculate trimester
    df['Trimester'] = df['Month'].apply(get_trimester)
    
    print("\n=== Total After Processing (in cents) ===")
    print(f"Total Base Tributável: {int(df['Base Tributável'].sum())}")
    print(f"Total IVA: {int(df['IVA'].sum())}")
    
    # Get unique years and trimesters
    year_trimesters = df.groupby(['Year', 'Trimester']).size().reset_index()[['Year', 'Trimester']]
    print("\n=== Found Years and Trimesters ===")
    for _, row in year_trimesters.iterrows():
        print(f"Year: {row['Year']}, Trimester: {row['Trimester']}")
    
    # Print totals by trimester
    trimester_totals = df.groupby(['Year', 'Trimester']).agg({
        'Base Tributável': 'sum',
        'IVA': 'sum'
    })
    print("\n=== Totals by Trimester (in cents) ===")
    print(trimester_totals.astype(int))
    
    # Group by year, trimester, month, and NIF
    grouped = df.groupby(['Year', 'Trimester', 'Month', 'NIF']).agg({
        'Base Tributável': 'sum',
        'IVA': 'sum'
    }).reset_index()
    
    return grouped, year_trimesters

def format_xml(element):
    # Convert ElementTree to string with proper formatting
    rough_string = ET.tostring(element, 'UTF-8')
    reparsed = minidom.parseString(rough_string)
    formatted = reparsed.toprettyxml(indent='\t')
    
    # Remove extra whitespace while preserving structure
    lines = formatted.splitlines()
    cleaned_lines = [line for line in lines if line.strip()]
    
    # Remove the XML declaration since we'll add it later
    if cleaned_lines[0].startswith('<?xml'):
        cleaned_lines = cleaned_lines[1:]
    
    return '\n'.join(cleaned_lines)

def get_trimester_months(trimester):
    # Get start and end months for a trimester (01T to 04T)
    trimester_num = int(trimester[:2])
    start_month = (trimester_num - 1) * 3 + 1
    end_month = start_month + 2
    return (start_month, start_month + 1, end_month)

def create_xml(template_path, output_path, data, year_trimesters, nif=None):
    # Register the namespace
    ET.register_namespace('', 'http://www.at.gov.pt/schemas/dpiva')
    
    # Create a new XML document
    root = ET.Element('{http://www.at.gov.pt/schemas/dpiva}dpiva')
    root.set('version', '06')
    
    # Try to get rosto section from template if it exists
    if template_path and os.path.exists(template_path):
        try:
            template_tree = ET.parse(template_path)
            template_root = template_tree.getroot()
            rosto = template_root.find('{http://www.at.gov.pt/schemas/dpiva}rosto')
            if rosto is not None:
                root.append(rosto)
        except Exception as e:
            print(f"Warning: Could not parse template XML: {e}")
            # Create basic rosto section if template fails
            rosto = ET.SubElement(root, '{http://www.at.gov.pt/schemas/dpiva}rosto')
            inicio = ET.SubElement(rosto, '{http://www.at.gov.pt/schemas/dpiva}inicio')
            if nif:
                ET.SubElement(inicio, '{http://www.at.gov.pt/schemas/dpiva}nif').text = nif
    else:
        # Create basic rosto section if no template
        rosto = ET.SubElement(root, '{http://www.at.gov.pt/schemas/dpiva}rosto')
        inicio = ET.SubElement(rosto, '{http://www.at.gov.pt/schemas/dpiva}inicio')
        if nif:
            ET.SubElement(inicio, '{http://www.at.gov.pt/schemas/dpiva}nif').text = nif
    
    # Process each year and trimester found in the data
    for _, row in year_trimesters.sort_values(['Year', 'Trimester'], ascending=[False, False]).iterrows():
        year = str(int(row['Year']))
        trimester = row['Trimester']
        trimester_id = f"{year[-2:]}{trimester}"  # e.g., "2412T"
        
        start_month, _, end_month = get_trimester_months(trimester)
        
        print(f"\n=== Processing Trimester {trimester_id} ===")
        print(f"Months {start_month} to {end_month}")
        
        # Filter data for this trimester's months
        trimester_data = data[
            (data['Year'] == int(year)) & 
            (data['Month'].between(start_month, end_month))
        ].copy()
        
        print(f"\nFound {len(trimester_data)} entries")
        if not trimester_data.empty:
            print("\nDetailed entries (in cents):")
            for _, row in trimester_data.iterrows():
                print(f"Month: {row['Month']:02d}, NIF: {row['NIF']}, BT: {int(row['Base Tributável'])}, IVA: {int(row['IVA'])}")
        
        # Sort by month and NIF to ensure consistent order
        trimester_data.sort_values(['Month', 'NIF'], inplace=True)
        
        # Calculate totals for the trimester
        bt_total = int(trimester_data['Base Tributável'].sum())
        iva_total = int(trimester_data['IVA'].sum())
        
        print(f"\nTrimester totals (in cents):")
        print(f"Base Tributável: {bt_total}")
        print(f"IVA: {iva_total}")
        
        # Create fornecedores element
        fornecedores = ET.SubElement(root, '{http://www.at.gov.pt/schemas/dpiva}fornecedores')
        fornecedores.set('id', trimester_id)
        
        relacao = ET.SubElement(fornecedores, '{http://www.at.gov.pt/schemas/dpiva}relacao')
        
        # Add basic elements
        ET.SubElement(relacao, '{http://www.at.gov.pt/schemas/dpiva}anoDeducao').text = year
        ET.SubElement(relacao, '{http://www.at.gov.pt/schemas/dpiva}periodoDeducao').text = trimester
        
        ET.SubElement(relacao, '{http://www.at.gov.pt/schemas/dpiva}btAquisicoesTotal').text = str(bt_total)
        ET.SubElement(relacao, '{http://www.at.gov.pt/schemas/dpiva}ivaAquisicoesTotal').text = str(iva_total)
        
        if not trimester_data.empty:
            # Create campo24 element
            campo24 = ET.SubElement(relacao, '{http://www.at.gov.pt/schemas/dpiva}campo24')
            
            # Add entries for each supplier-month combination
            for idx, row in trimester_data.iterrows():
                item = ET.SubElement(campo24, '{http://www.at.gov.pt/schemas/dpiva}campo24Item')
                if idx == trimester_data.index[0]:
                    item.set('row', '1')
                
                bt_value = int(row['Base Tributável'])
                iva_value = int(row['IVA'])
                
                ET.SubElement(item, '{http://www.at.gov.pt/schemas/dpiva}anoEmissao').text = str(int(row['Year']))
                ET.SubElement(item, '{http://www.at.gov.pt/schemas/dpiva}btAquisicoes').text = str(bt_value)
                ET.SubElement(item, '{http://www.at.gov.pt/schemas/dpiva}ivaAquisicoes').text = str(iva_value)
                ET.SubElement(item, '{http://www.at.gov.pt/schemas/dpiva}mesEmissao').text = f"{int(row['Month']):02d}"
                ET.SubElement(item, '{http://www.at.gov.pt/schemas/dpiva}nif').text = row['NIF']
                ET.SubElement(item, '{http://www.at.gov.pt/schemas/dpiva}prefixoNIF').text = 'PT'
    
    # Write the formatted XML to a new file
    formatted_xml = format_xml(root)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(formatted_xml)

def main():
    # Get command line arguments with fallbacks
    invoice_file = sys.argv[1] if len(sys.argv) > 1 else 'faturas.csv'
    template_file = sys.argv[2] if len(sys.argv) > 2 else 'dpiva-template.xml'
    output_file = sys.argv[3] if len(sys.argv) > 3 else 'dp-iva-auto.xml'
    
    # Check if invoice file exists
    if not os.path.exists(invoice_file):
        print(f"Error: Invoice file '{invoice_file}' not found.")
        sys.exit(1)
    
    # Process the CSV file
    data, year_trimesters = process_csv(invoice_file)
    
    # Try to extract NIF from template if it exists
    nif = None
    if os.path.exists(template_file):
        try:
            template_tree = ET.parse(template_file)
            template_root = template_tree.getroot()
            nif_elem = template_root.find('.//{http://www.at.gov.pt/schemas/dpiva}nif')
            if nif_elem is not None:
                nif = nif_elem.text
        except:
            pass
    
    # Create the new XML file
    create_xml(template_file, output_file, data, year_trimesters, nif)
    print(f"\nXML file generated: {output_file}")

if __name__ == "__main__":
    main()
