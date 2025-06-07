import requests
import pandas as pd
import os
import logging
from datetime import datetime, timedelta
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download_bkam_monia_csvs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_date_range(start_date, end_date):
    """Génère une liste de dates entre start_date et end_date, en excluant les week-ends et les jours fériés."""
    dates = []
    current_date = start_date
    while current_date <= end_date:
        # Exclure samedis (weekday=5) et dimanches (weekday=6)
        if current_date.weekday() < 5:
            # Exclure les jours fériés (1er janvier et 1er mai de chaque année)
            if not (current_date.day == 1 and current_date.month in [1, 5]):
                dates.append(current_date)
        current_date += timedelta(days=1)
    return dates

def construct_url(date):
    """Construit l'URL directe pour télécharger le CSV pour une date donnée."""
    date_str = date.strftime("%d/%m/%Y")
    encoded_date = quote(date_str)
    base_url = "https://www.bkam.ma/export/blockcsv/566622/30551c1667f5f2004fb0019220d41795/4734c7b73113d8d72895a19090974066"
    block_id = "4734c7b73113d8d72895a19090974066"
    return f"{base_url}?date={encoded_date}&block={block_id}"

def download_csv(url, date, output_dir, failed_dir, max_retries=3):
    """Télécharge le fichier CSV et l'enregistre localement avec réessais."""
    session = requests.Session()
    retries = Retry(total=max_retries, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/csv,application/octet-stream,*/*",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.bkam.ma/",
            "Connection": "keep-alive"
        }
        response = session.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        # Journaliser les informations de la réponse
        content_type = response.headers.get('Content-Type', '').lower()
        status_code = response.status_code
        content_snippet = response.content[:500].decode('utf-8', errors='ignore')
        logger.debug(
            f"Réponse pour {date.strftime('%d/%m/%Y')} - Status: {status_code}, Content-Type: {content_type}, Snippet: {content_snippet[:100]}...")

        # Vérifier si la réponse est un CSV
        if 'text/csv' not in content_type and 'application/octet-stream' not in content_type:
            logger.warning(f"Contenu non-CSV pour {date.strftime('%d/%m/%Y')}: {content_type}")
            failed_filename = os.path.join(failed_dir, f"failed_{date.strftime('%Y%m%d')}.html")
            os.makedirs(failed_dir, exist_ok=True)
            with open(failed_filename, 'w', encoding='utf-8') as f:
                f.write(content_snippet)
            logger.info(f"Réponse problématique sauvegardée: {failed_filename}")
            return None

        # Écrire temporairement pour tester
        temp_filename = os.path.join(output_dir, f"temp_{date.strftime('%Y%m%d')}.csv")
        os.makedirs(output_dir, exist_ok=True)
        with open(temp_filename, 'wb') as f:
            f.write(response.content)

        # Tenter de lire le CSV pour validation avec différents encodages
        encodings = ['utf-8', 'latin-1', 'iso-8859-1']
        df = None
        for enc in encodings:
            try:
                # Lire toutes les colonnes pour débogage
                temp_df = pd.read_csv(temp_filename, sep=';', encoding=enc, skiprows=2)
                logger.debug(f"En-têtes détectés avec {enc}: {temp_df.columns.tolist()}")
                # Vérifier si les colonnes attendues sont présentes
                if all(col in temp_df.columns for col in ['Indice MONIA', 'Volume JJ', 'Date de référence', 'Date de publication']):
                    df = temp_df[['Indice MONIA', 'Volume JJ', 'Date de référence', 'Date de publication']].copy()
                    logger.debug(f"Encodage réussi avec {enc}")
                    break
            except UnicodeDecodeError:
                logger.debug(f"Échec de l'encodage {enc}")
                continue
            except Exception as e:
                logger.debug(f"Erreur avec {enc}: {e}")
                continue

        if df is None:
            raise ValueError("Aucun encodage valide trouvé pour lire le fichier avec les colonnes attendues.")

        if df.empty:
            raise ValueError("Aucune donnée valide trouvée dans le CSV.")

        # Si valide, renommer
        date_str = date.strftime("%Y%m%d")
        csv_filename = os.path.join(output_dir, f"monia_{date_str}.csv")
        df.to_csv(csv_filename, index=False, sep=';', encoding='utf-8')
        logger.info(f"CSV téléchargé pour {date.strftime('%d/%m/%Y')}: {csv_filename}")
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        return csv_filename

    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors du téléchargement du CSV pour {date.strftime('%d/%m/%Y')}: {e}")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue pour {date.strftime('%d/%m/%Y')}: {type(e).__name__} - {str(e)}")
        return None

def main():
    # Paramètres pour la période
    start_date = datetime(2020, 1, 2)  # Début au 2 janvier 2020
    end_date = datetime(2025, 6, 5)    # Fin au 5 juin 2025

    output_dir = "bkam_monia_csvs"
    failed_dir = "failed_downloads_monia"

    # Générer les dates (jours ouvrables uniquement, sans 1er janvier ni 1er mai)
    dates = generate_date_range(start_date, end_date)
    logger.info(
        f"Extraction des données pour {len(dates)} jours ouvrables: {start_date.strftime('%d/%m/%Y')} à {end_date.strftime('%d/%m/%Y')}")

    # Liste pour stocker les chemins des CSVs
    csv_files = []

    # Boucle sur chaque date
    for date in dates:
        url = construct_url(date)
        logger.debug(f"Traitement de l'URL: {url}")
        csv_filename = download_csv(url, date, output_dir, failed_dir)
        if csv_filename:
            csv_files.append(csv_filename)

    logger.info(f"{len(csv_files)} fichiers CSV téléchargés dans {output_dir}.")

if __name__ == "__main__":
    main()