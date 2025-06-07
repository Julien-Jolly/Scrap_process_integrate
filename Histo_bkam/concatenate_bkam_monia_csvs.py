import os
import glob
import pandas as pd
import logging

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('concatenate_bkam_monia_csvs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def concatenate_bkam_monia_csvs(input_dir="bkam_monia_csvs", output_file="combined_monia_2020_2025.csv"):
    """
    Liste et concatène les fichiers CSV du répertoire de téléchargement en un seul fichier.

    Args:
        input_dir (str): Répertoire contenant les fichiers CSV (par défaut: 'bkam_monia_csvs').
        output_file (str): Nom du fichier CSV combiné (par défaut: 'combined_monia_2020_2025.csv').

    Returns:
        bool: True si la concaténation réussit, False sinon.
    """
    # Vérifier si le répertoire existe
    if not os.path.exists(input_dir):
        logger.error(f"Le répertoire {input_dir} n'existe pas.")
        return False

    # Lister tous les fichiers CSV
    csv_pattern = os.path.join(input_dir, "monia_*.csv")
    csv_files = glob.glob(csv_pattern)

    if not csv_files:
        logger.warning(f"Aucun fichier CSV trouvé dans {input_dir}.")
        return False

    logger.info(f"{len(csv_files)} fichiers CSV trouvés dans {input_dir}.")

    # Liste pour stocker les DataFrames
    all_dfs = []

    # Traiter chaque fichier CSV
    for csv_file in csv_files:
        try:
            # Lire les colonnes spécifiées sans ajouter de colonne Date
            df = pd.read_csv(
                csv_file,
                sep=';',
                encoding='utf-8',
                usecols=['Indice MONIA', 'Volume JJ', 'Date de référence', 'Date de publication']
            )
            if df.empty:
                logger.warning(f"Aucune donnée valide dans {csv_file}.")
                continue
            all_dfs.append(df)
            logger.debug(f"Fichier {csv_file} lu: {df.shape}")
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de {csv_file}: {e}")
            continue

    # Concaténer les DataFrames
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        # Garder uniquement les colonnes originales
        cols = ['Indice MONIA', 'Volume JJ', 'Date de référence', 'Date de publication']
        combined_df = combined_df[cols]

        # Sauvegarder le fichier combiné
        output_path = os.path.join(input_dir, output_file)
        combined_df.to_csv(output_path, index=False, sep=';', encoding='utf-8-sig')
        logger.info(f"Fichier combiné sauvegardé: {output_path} ({combined_df.shape})")
        return True
    else:
        logger.warning("Aucun fichier CSV valide n'a pu être concaténé.")
        return False

if __name__ == "__main__":
    concatenate_bkam_monia_csvs()