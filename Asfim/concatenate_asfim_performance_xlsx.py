import os
import pandas as pd
from datetime import datetime
import re

# En-têtes communs pour tous les types
target_fields = [
    "CODE ISIN", "Code Maroclear", "OPCVM", "Société de Gestion", "Nature juridique",
    "Classification", "Sensibilité", "Indice Bentchmark", "Périodicité VL", "Souscripteurs",
    "Affectation des résultats", "Commission de souscription", "Commission de rachat",
    "Frais de gestion", "Dépositaire", "Réseau placeur", "AN", "VL", "YTD", "1 jour",
    "1 semaine", "1 mois", "3 mois", "6 mois", "1 an", "2 ans", "3 ans", "5 ans"
]

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

            # Lire le fichier avec toutes les colonnes pour détecter "Promoteur" et le nombre de colonnes
            df_initial = pd.read_excel(file_path, header=0)

            # Détecter la présence de "Promoteur" et le nombre total de colonnes
            has_promoteur = "Promoteurs" in df_initial.columns
            total_cols = len(df_initial.columns)
            promoteur_index = 14 if has_promoteur else -1

            # Définir les colonnes à lire selon le type et la présence de "Promoteur"
            if file_type in ["quotidien", "hebdomadaire"]:
                usecols = list(range(min(28, total_cols)))  # Prendre toutes les colonnes jusqu'à 28
                skip_rows = 1
            else:  # autres
                if has_promoteur:
                    usecols = [i for i in range(total_cols) if i != promoteur_index and i < 29]  # Exclure "Promoteur" et limiter à 29
                    usecols = [i for i in usecols if i in list(range(14)) + list(range(15, 29))]  # Prendre 0-13 et 15-28
                else:
                    usecols = list(range(min(28, total_cols)))  # Prendre toutes les colonnes jusqu'à 28
                skip_rows = 1

            # Relire le fichier avec les colonnes et lignes spécifiques
            df = pd.read_excel(file_path, header=0, skiprows=skip_rows, usecols=usecols)

            # Renommer les colonnes pour correspondre aux en-têtes attendus
            df.columns = target_fields[:len(df.columns)]

            # Ajouter les colonnes Date et Type
            date_str = filename[:10] if re.match(r'^\d{2}-\d{2}-\d{4}', filename) else filename.split("au-")[-1].replace(".xlsx", "")
            df["Date"] = datetime.strptime(date_str, "%d-%m-%Y")
            df["Type"] = file_type

            # Ajouter au liste des DataFrames
            dataframes.append(df)

            # Journalisation des mappings
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(f"\n--- Fichier traité : {filename} (Type: {file_type}) ---\n")
                log.write(f"Présence de 'Promoteur' : {has_promoteur}\n")
                log.write(f"Nombre total de colonnes : {total_cols}\n")
                log.write(f"Indice de 'Promoteur' : {promoteur_index}\n")
                log.write(f"Colonnes utilisées : {usecols}\n")
                log.write("Emplacements des champs :\n")
                for i, col in enumerate(df.columns):
                    log.write(f"{col}: Colonne {i}\n")

        except Exception as e:
            print(f"Erreur lors de la lecture de {filename}: {str(e)}")

# Concaténer tous les DataFrames
if dataframes:
    consolidated_df = pd.concat(dataframes, ignore_index=True)
    consolidated_df.to_csv(output_file, index=False, encoding='utf-8-sig', sep=';')
    print(f"Fichier consolidé généré : {output_file}")
else:
    print("Aucun fichier valide à concaténer.")