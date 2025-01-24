# Conversor de Faturas para Anexo de Fornecedores da Declaração Periódica de IVA

Cria automaticamente o anexo de fornecedores para a declaração periódica do IVA trimestral a partir das faturas exportadas do e-fatura. Uso comercial não é autorizado.

Este programa processa faturas em formato CSV e gera um ficheiro XML compatível com a Declaração Periódica de IVA (DPIVA) da Autoridade Tributária e Aduaneira portuguesa.

## Pré-requisitos

- Python 3.8 ou superior
- pip (gestor de pacotes do Python)

## Instalação

1. Recomendo criação de um ambiente virtual para isolar as dependências:

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar o ambiente virtual
# No Windows:
venv\Scripts\activate
# No macOS/Linux:
source venv/bin/activate
```

2. Instalar as dependências necessárias:

```bash
pip install pandas
```

## Utilização

O programa pode ser executado de várias formas:

1. Forma básica (utilizando nomes predefinidos):
```bash
python3 process_invoices.py
```
Neste caso, o programa irá procurar:
- `faturas.csv` - ficheiro de entrada com as faturas
- `dpiva-template.xml` - modelo XML opcional
- `dp-iva-auto.xml` - ficheiro de saída

2. Especificando os ficheiros:
```bash
python3 process_invoices.py caminho/faturas.csv caminho/modelo.xml caminho/resultado.xml
```

## Formato do Ficheiro CSV
Podes obter isto no efatura, exporta apenas as faturas afetas a atividade e no periodo que pretendes.

O ficheiro CSV deve:
- Utilizar ponto e vírgula (;) como separador
- Conter as seguintes colunas:
  - `Data Emissão` - formato dd/mm/aaaa
  - `Emitente` - formato "NIF - Nome da Empresa"
  - `Base Tributável` - valor em euros (ex: 123,45 €)
  - `IVA` - valor em euros (ex: 28,39 €)

Exemplo:
```csv
Data Emissão;Emitente;Base Tributável;IVA
02/01/2024;123456789 - Empresa ABC;100,00 €;23,00 €
```

## Funcionalidades

- Deteta automaticamente os anos e trimestres presentes nos dados
- Agrupa as faturas por trimestre
- Mantém os valores em cêntimos sem arredondamentos
- Gera XML compatível com o formato da AT
- Suporta modelo XML opcional para manter dados do `<rosto>`
- Ordena os trimestres do mais recente para o mais antigo

## Notas

- Os valores são guardados em cêntimos no XML (ex: 100,50€ é guardado como 10050)
- O NIF é extraído automaticamente do modelo XML, se disponível
- Se não for fornecido um modelo, é criada uma estrutura XML básica
- Os ficheiros são processados em UTF-8 
