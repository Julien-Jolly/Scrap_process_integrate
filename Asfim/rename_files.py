import os
import re

# Chemin du répertoire temporaire
temp_dir = "temp_renaming_folder"

# Vérifier si le répertoire existe
if not os.path.exists(temp_dir):
    print(f"Le répertoire {temp_dir} n'existe pas. Créez-le et placez-y les fichiers à renommer.")
    exit(1)

# Parcourir les fichiers dans le répertoire temporaire
for filename in os.listdir(temp_dir):
    if filename.lower().endswith('.xlsx'):
        # Étape 1 : Remplacer les espaces dans le préfixe par des tirets
        new_filename = filename.replace("Tableau des Performances Hebdomadaires", "Tableau-des-Performances-Hebdomadaires")
        new_filename = new_filename.replace("Tableau des performances quotidiennes", "Tableau-des-performances-quotidiennes")

        # Étape 2 : Ajouter un tiret entre "Hebdomadaires"/"quotidiennes" et "au" si manquant
        new_filename = new_filename.replace("Hebdomadaires au", "Hebdomadaires-au")
        new_filename = new_filename.replace("quotidiennes au", "quotidiennes-au")

        # Étape 3 : Supprimer l'espace entre "au" et la date (ex. "au 30-05-2025" -> "au-30-05-2025")
        new_filename = re.sub(r'au\s+(\d{2}-\d{2}-\d{4})', r'au-\1', new_filename)

        # Étape 4 : Corriger les dates avec espaces (ex. "07 07 2023" -> "07-07-2023")
        date_with_spaces = re.search(r'au-(\d{2}) (\d{2}) (\d{4})\.xlsx$', new_filename)
        if date_with_spaces:
            day, month, year = date_with_spaces.groups()
            new_filename = new_filename.replace(f"{day} {month} {year}", f"{day}-{month}-{year}")

        # Étape 5 : Supprimer les suffixes indésirables (ex. "-1" ou "-1667572513263")
        suffix_pattern = re.search(r'^(.*?\d{2}-\d{2}-\d{4})\.xlsx-[\w\d-]+\.xlsx$', new_filename)
        if suffix_pattern:
            new_filename = f"{suffix_pattern.group(1)}.xlsx"

        # Si le nom a changé, renommer le fichier
        if new_filename != filename:
            old_path = os.path.join(temp_dir, filename)
            new_path = os.path.join(temp_dir, new_filename)
            try:
                os.rename(old_path, new_path)
                print(f"Renommé : {filename} -> {new_filename}")
            except Exception as e:
                print(f"Erreur lors du renommage de {filename} : {e}")
        else:
            print(f"Aucune modification nécessaire pour : {filename}")