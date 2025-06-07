import os
import pandas as pd
from datetime import datetime
import re

# Champs par type de fichier (attendus)
target_fields = {
    "quotidien": [
        "CODE ISIN", "Code Maroclear", "OPCVM", "Société de Gestion", "Nature juridique",
        "Classification", "Sensibilité", "Indice Benchmark", "Périodicité VL", "Souscripteurs",
        "Affectation des résultats", "Commission de souscription", "Commission de rachat",
        "Frais de gestion", "Dépositaire", "Réseau placeur", "AN", "VL", "YTD", "1 jour",
        "1 semaine", "1 mois", "3 mois", "6 mois", "1 an", "2 ans", "3 ans", "5 ans"
    ],
    "hebdomadaire": [
        "CODE ISIN", "Code Maroclear", "Dénomination OPCVM", "Société de Gestion", "Nature juridique",
        "Classification", "Sensibilité", "Indice Benchmark", "Périodicité VL", "Souscripteurs",
        "Affectation des résultats", "Commission de souscription", "Commission de rachat",
        "Frais de gestion", "Dépositaire", "Réseau placeur", "AN", "VL", "YTD", "1 jour",
        "1 semaine", "1 mois", "3 mois", "6 mois", "1 an", "2 ans", "3 ans", "5 ans"
    ],
    "autres": [
        "CODE ISIN", "Code Maroclear", "Dénomination OPCVM", "Société de Gestion", "Nature juridique",
        "Classification", "Sensibilité", "Indice Benchmark", "Périodicité VL", "Souscripteurs",
        "Affectation des résultats", "Commission de souscription", "Commission de rachat",
        "Frais de gestion", "Dépositaire", "Réseau placeur", "AN au ", "VL au ", "YTD",
        "1 jour", "1 semaine", "1 mois", "3 mois", "6 mois", "1 an", "2 ans", "3 ans", "5 ans"
    ]
}

# Répertoire des fichiers
data_dir = "asfim_performance_xlsx"
output_file = "consolidated_output.csv"
log_file = "field_mapping_log.txt"

# Déterminer le type de fichier en fonction du nom
def get_file_type(filename):
    if "quotidien" in filename.lower():
        return "quotidien"
    elif "hebdomadaire" in filename.lower():
        return "hebdomadaire"
    else:
        return "autres"

# Liste pour stocker les DataFrames
dataframes = []

# Parcourir tous les fichiers .xlsx
for filename in os.listdir(data_dir):
    if filename.lower().endswith('.xlsx'):
        file_path = os.path.join(data_dir, filename)
        print(f"Traitement de {filename}...")
        try:
            file_type = get_file_type(filename)
            expected_fields = target_fields[file_type]

            # Lire le fichier avec toutes les colonnes pour détecter "Promoteur" et le nombre de colonnes
            df_initial = pd.read_excel(file_path, header=0)

            # Détecter la présence de "Promoteur" et le nombre total de colonnes
            has_promoteur = "Promoteur" in df_initial.columns
            total_cols = len(df_initial.columns)
            promoteur_index = df_initial.columns.get_loc("Promoteur") if has_promoteur else -1

            # Définir les colonnes à lire selon la présence de "Promoteur" et le nombre de colonnes
            if file_type in ["quotidien", "hebdomadaire"]:
                usecols = list(range(min(28, total_cols)))
                skip_rows = 1  # Données à partir de ligne 2
                header_row = 0  # En-tête en ligne 1
            else:  # autres
                if has_promoteur:
                    usecols = [i for i in range(total_cols) if i != promoteur_index]
                else:
                    usecols = list(range(min(29, total_cols)))
                skip_rows = 1  # Données à partir de ligne 2
                header_row = 0  # En-tête en ligne 1

            # Relire le fichier avec les colonnes et lignes spécifiques
            df = pd.read_excel(file_path, header=header_row, skiprows=skip_rows, usecols=usecols)

            # Mapper les colonnes aux champs attendus (basé sur les indices fixes)
            column_mapping = {field: df.columns[i] if i < len(df.columns) else None for i, field in enumerate(expected_fields)}

            # Renommer les colonnes pour correspondre aux champs attendus
            new_df = pd.DataFrame()
            for field, actual_col in column_mapping.items():
                if actual_col is not None and actual_col in df.columns:
                    new_df[field] = df[actual_col]
                else:
                    new_df[field] = pd.NA  # Remplir avec NA si la colonne est absente

            # Journalisation des mappings
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(f"\n--- Fichier traité : {filename} (Type: {file_type}) ---\n")
                log.write(f"Présence de 'Promoteur' : {has_promoteur}\n")
                log.write(f"Nombre total de colonnes : {total_cols}\n")
                log.write(f"Indice de 'Promoteur' : {promoteur_index}\n")
                log.write("Emplacements des champs :\n")
                for i, field in enumerate(expected_fields):
                    actual_col = df.columns[i] if i < len(df.columns) else "Hors limites"
                    log.write(f"{field}: Colonne {i} (Valeur : {actual_col})\n")

            # Extraire la date du nom de fichier
            date_str = filename[:10] if re.match(r'^\d{2}-\d{2}-\d{4}', filename) else filename.split("au-")[-1].replace(".xlsx", "")
            new_df["Date"] = datetime.strptime(date_str, "%d-%m-%Y")
            new_df["Type"] = file_type  # Ajouter la colonne Type

            dataframes.append(new_df)

        except Exception as e:
            print(f"Erreur lors de la lecture de {filename}: {str(e)}")

# Concaténer tous les DataFrames
if dataframes:
    consolidated_df = pd.concat(dataframes, ignore_index=True)
    consolidated_df.to_csv(output_file, index=False, encoding='utf-8-sig', sep=';')
    print(f"Fichier consolidé généré : {output_file}")
else:
    print("Aucun fichier valide à concaténer.")