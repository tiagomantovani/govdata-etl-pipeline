# src/extraction/ibge_extractor.py
import requests
import json
import os
from datetime import datetime
from src.utils.config import IBGE_API_BASE, RAW_DATA_DIR

class IBGEExtractor:
    def __init__(self):
        # Usar API SIDRA (mais estável)
        self.base_url_sidra = "https://apisidra.ibge.gov.br/values"
        self.base_url_agregados = "https://servicodados.ibge.gov.br/api/v3/agregados"
        
    def get_populacao(self):
        """Extrai dados de população do IBGE (Tabela 4714)"""
        # Usar API SIDRA - mais estável
        url = f"{self.base_url_sidra}/t/4714/n3/all/v/93/p/2022"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Salvar dados brutos
            filename = f"ibge_populacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(RAW_DATA_DIR, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Dados de população salvos em: {filepath}")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao extrair dados de população: {e}")
            return None
    
    def get_pib(self):
        """Extrai dados de PIB do IBGE (Tabela 5938)"""
        # Endpoint correto: PIB total (v/37) e per capita (v/543) por UF
        url = f"{self.base_url_sidra}/t/5938/n3/all/v/37,543/p/last"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            filename = f"ibge_pib_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(RAW_DATA_DIR, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Dados de PIB salvos em: {filepath}")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao extrair dados de PIB: {e}")
            return None
    
    def get_estados(self):
        """Extrai lista de estados"""
        # Esta API continua funcionando
        url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            filename = f"ibge_estados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(RAW_DATA_DIR, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Lista de estados salva em: {filepath}")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao extrair estados: {e}")
            return None

# Teste rápido
if __name__ == "__main__":
    extractor = IBGEExtractor()
    print("Testando extração de dados...")
    extractor.get_estados()
    extractor.get_populacao()
    extractor.get_pib()