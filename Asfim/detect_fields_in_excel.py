import os
import pandas as pd
import re
from collections import defaultdict

# Champs par type de fichier
target_fields = {
    "quotidien": [
        "CODE ISIN", "Code Maroclear", "OPCVM", "Société de Gestion", "Nature juridique",
        "Classification", "Sensibilité", "Indice Bentchmark", "Périodicité VL", "Souscripteurs",
        "Affectation des résultats", "Commission de souscription", "Commission de rachat",
        "Frais de gestion", "Dépositaire", "Réseau placeur", "AN", "VL", "YTD", "1 jour",
        "1 semaine", "1 mois", "3 mois", "6 mois", "1 an", "2 ans", "3 ans", "5 ans"
    ],
    "hebdomadaire": [
        "CODE ISIN", "Code Maroclear", "Dénomination OPCVM", "Société de Gestion", "Nature juridique",
        "Classification", "Sensibilité", "Indice Bentchmark", "Périodicité VL", "Souscripteurs",
        "Affectation des résultats", "Commission de souscription", "Commission de rachat",
        "Frais de gestion", "Dépositaire", "Réseau placeur", "AN", "VL", "YTD", "1 jour",
        "1 semaine", "1 mois", "3 mois", "6 mois", "1 an", "2 ans", "3 ans", "5 ans"
    ],
    "autres": [
        "CODE ISIN", "Code Maroclear", "Dénomination OPCVM", "Société de Gestion", "Nature juridique",
        "Classification", "Sensibilité", "Indice Bentchmark", "Périodicité VL", "Souscripteurs",
        "Affectation des résultats", "Commission de souscription", "Commission de rachat",
        "Frais de gestion", "Promoteurs", "Dépositaire", "Réseau placeur", "AN au ", "VL au ",
        "1 jour", "1 semaine", "1 mois", "3 mois", "6 mois", "1 an", "2 ans", "3 ans", "5 ans"
    ]
}

# Répertoire des fichiers
data_dir = "asfim_performance_xlsx"

# Fichier de log
log_file = "field_detection_log.txt"

# Dictionnaire pour stocker les résultats
results = defaultdict(list)

# Déterminer le type de fichier en fonction du nom
def get_file_type(filename):
    if filename.startswith("Tableau-des-performances-quotidiennes"):
        return "quotidien"
    elif any(filename.startswith(f"{d:02d}-{m:02d}-") for d in range(1, 32) for m in range(1, 13)):
        return "hebdomadaire"  # Hypothèse : les fichiers jj-mm-aaaa sont hebdomadaires
    else:
        return "autres"

# Parcourir tous les fichiers .xlsx
for filename in os.listdir(data_dir):
    if filename.lower().endswith('.xlsx'):
        file_path = os.path.join(data_dir, filename)
        try:
            file_type = get_file_type(filename)
            fields = target_fields[file_type]

            # Lire les premières lignes (2e ligne pour quotidien/hebdomadaire, 1re fusionnée pour autres)
            if file_type in ["quotidien", "hebdomadaire"]:
                df = pd.read_excel(file_path, header=1, nrows=1)
            else:  # autres
                df = pd.read_excel(file_path, header=None, nrows=2)
                df = df.iloc[0].fillna(df.iloc[1])  # Fusionner 1re et 2e ligne

            headers = df.dropna().astype(str).tolist()

            # Résultats pour ce fichier
            file_results = {"filename": filename, "type": file_type, "matches": {}}

            # Recherche approximative pour chaque champ
            for field in fields:
                found = False
                for i, header in enumerate(headers):
                    if re.search(r'\b' + re.escape(field).replace(r'\ ', r'\s*') + r'\b', header, re.IGNORECASE):
                        file_results["matches"][field] = {"column": i, "exact_match": header}
                        found = True
                        break
                    for offset in [-2, -1, 1, 2]:
                        adj_index = i + offset
                        if 0 <= adj_index < len(headers):
                            if re.search(r'\b' + re.escape(field).replace(r'\ ', r'\s*') + r'\b', headers[adj_index], re.IGNORECASE):
                                file_results["matches"][field] = {"column": adj_index, "exact_match": headers[adj_index]}
                                found = True
                                break
                    if found:
                        break

                if not found:
                    file_results["matches"][field] = {"column": None, "exact_match": None}

            results["files"].append(file_results)

        except Exception as e:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"Erreur lors de la lecture de {filename}: {str(e)}\n")

# Écrire les résultats dans le fichier de log
with open(log_file, 'w', encoding='utf-8') as f:
    for file_result in results["files"]:
        f.write(f"\nFichier: {file_result['filename']} (Type: {file_result['type']})\n")
        for field, info in file_result["matches"].items():
            f.write(f"  {field}: colonne {info['column']} (correspondance: {info['exact_match']})\n")
        f.write("-" * 50 + "\n")

print(f"Analyse terminée. Résultats enregistrés dans {log_file}")