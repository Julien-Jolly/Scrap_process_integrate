import os
import re
from collections import defaultdict
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('doublon_remover.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def normalize_filename(filename):
    """
    Normalise le nom de fichier pour détecter les doublons.
    Exemple : "Tableau-des-performances-quotidiennes-au-15-06-2022.xlsx" et
              "Tableau-des-performances-quotidiennes-au-15-06-2022-1.xlsx" sont considérés comme identiques.

    Args:
        filename (str): Nom du fichier.

    Returns:
        str: Nom normalisé (sans suffixe de doublon ni extension).
    """
    # Supprimer l'extension
    name, _ = os.path.splitext(filename)
    # Supprimer les suffixes comme "-1", "-2", etc.
    name = re.sub(r'-\d+$', '', name)
    return name.lower()


def remove_duplicates(directory="asfim_performance_xlsx"):
    """
    Identifie et supprime les doublons dans le répertoire spécifié.
    Conserve le fichier le plus récent (basé sur la date de modification).

    Args:
        directory (str): Chemin du répertoire contenant les fichiers.
    """
    # Vérifier que le répertoire existe
    if not os.path.exists(directory):
        logger.error(f"Le répertoire {directory} n'existe pas.")
        return

    # Dictionnaire pour stocker les fichiers par nom normalisé
    file_groups = defaultdict(list)

    # Lister tous les fichiers dans le répertoire
    for filename in os.listdir(directory):
        if filename.lower().endswith('.xlsx'):
            normalized_name = normalize_filename(filename)
            file_path = os.path.join(directory, filename)
            # Récupérer la date de modification
            mtime = os.path.getmtime(file_path)
            file_groups[normalized_name].append((filename, file_path, mtime))

    # Compteur de doublons
    total_duplicates = 0
    total_files = len([f for f in os.listdir(directory) if f.lower().endswith('.xlsx')])
    logger.info(f"Nombre total de fichiers .xlsx dans {directory} : {total_files}")

    # Analyser chaque groupe de fichiers
    for normalized_name, files in file_groups.items():
        if len(files) > 1:  # Si doublons détectés
            total_duplicates += len(files) - 1
            logger.info(f"Doublons détectés pour '{normalized_name}' : {len(files)} fichiers")

            # Trier par date de modification (du plus récent au plus ancien)
            files.sort(key=lambda x: x[2], reverse=True)

            # Conserver le fichier le plus récent
            keep_file = files[0]
            logger.info(f"Conservation du fichier le plus récent : {keep_file[0]} (modifié le {keep_file[2]})")

            # Supprimer les autres fichiers
            for file_to_remove in files[1:]:
                try:
                    os.remove(file_to_remove[1])
                    logger.info(f"Suppression du doublon : {file_to_remove[0]}")
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression de {file_to_remove[0]} : {e}")

    if total_duplicates == 0:
        logger.info("Aucun doublon détecté.")
    else:
        new_total = len([f for f in os.listdir(directory) if f.lower().endswith('.xlsx')])
        logger.info(f"Nombre de doublons supprimés : {total_duplicates}")
        logger.info(f"Nombre de fichiers restants : {new_total}")


if __name__ == "__main__":
    remove_duplicates()