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
        logging.FileHandler('extract_bkam_exchange_rates_direct.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Dictionnaire de correspondance des devises aux codes ISO
currency_mapping = {
    "1 EURO": "EUR",
    "1 DOLLAR U.S.A.": "USD",
    "1 DOLLAR CANADIEN": "CAD",
    "1 LIVRE STERLING": "GBP",
    "1 LIVRE GIBRALTAR": "GIP",
    "1 FRANC SUISSE": "CHF",
    "100 COURONNES DANOISES": "DKK",
    "100 COURONNES SUEDOISES": "SEK",
    "100 COURONNES NORVEGIENNES": "NOK",
    "1 RIYAL SAOUDIEN": "SAR",
    "1 DINAR KOWEITIEN": "KWD",
    "1 DIRHAM E.A.U.": "AED",
    "1 RIYAL QATARI": "QAR",
    "1 DINAR BAHREINI": "BHD",
    "100 YENS JAPONAIS": "JPY",
    "10 DINARS ALGERIENS": "DZD",
    "1 DINAR TUNISIEN": "TND",
    "1 DINAR LIBYEN": "LYD",
    "100 OUGUIYAS MAURITANIENNES": "MRO",
    "1 RIYAL OMANI": "OMR",
    "1 REAL BRÉSILIEN": "BRL",  # Valeur correcte
    "1 REAL BRÃSILIEN": "BRL",  # Variante corrompue due à l'encodage
    "1 ROUBLE RUSSE": "RUB",
    "1 ROUPIE INDIENNE": "INR",
    "1 YUAN CHINOIS": "CNY",
    "1 DOLLAR AUSTRALIEN": "AUD",
    "1 RAND SUD-AFRICAIN": "ZAR",
    "1 LIVRE TURQUE": "TRY",
    "1 LIVRE EGYPTIENNE": "EGP",
    "1 DINAR JORDANIEN": "JOD",
    "100 FRANC CFA": "XOF"
}


def construct_url(date):
    """Construit l'URL directe pour télécharger le CSV pour une date donnée."""
    date_str = date.strftime("%d/%m/%Y")
    encoded_date = quote(date_str)
    base_url = "https://www.bkam.ma/export/blockcsv/4550/5312b6def4ad0a94c5a992522868ac0a/cc51b5ce6878a3dc655dae26c47fddf8"
    block_id = "cc51b5ce6878a3dc655dae26c47fddf8"
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
            "Referer": "https://www.bkam.ma/Marches/Principaux-indicateurs/Marche-des-changes/Cours-de-change/Cours-de-reference",
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

        # Tenter de lire et transformer les données avec différents encodages
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(temp_filename, sep=';', encoding=enc, usecols=['Devises', 'Moyen'], skiprows=3)
                logger.debug(f"Encodage réussi avec {enc}")
                break
            except UnicodeDecodeError:
                logger.debug(f"Échec de l'encodage {enc}")
                continue
            except Exception as e:
                logger.debug(f"Erreur avec {enc}: {e}")
                continue

        if df is None:
            raise ValueError("Aucun encodage valide trouvé pour lire le fichier.")

        # Transformer le champ Devises en code ISO
        df['Devises'] = df['Devises'].map(lambda x: currency_mapping.get(x.strip(), x))
        # Si valide, renommer
        date_str = date.strftime("%Y%m%d")
        csv_filename = os.path.join(output_dir, f"exchange_rates_{date_str}.csv")
        df.to_csv(csv_filename, index=False, sep=';', encoding='utf-8')
        logger.info(f"CSV téléchargé et transformé pour {date.strftime('%d/%m/%Y')}: {csv_filename}")
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
    # Calcul de la date de la veille
    yesterday = datetime.now() - timedelta(days=1)

    output_dir = "bkam_exchange_rates"
    failed_dir = "failed_downloads"

    # Téléchargement uniquement pour la veille
    url = construct_url(yesterday)
    logger.info(f"Téléchargement des données pour la veille: {yesterday.strftime('%d/%m/%Y')}")
    logger.debug(f"Traitement de l'URL: {url}")
    csv_filename = download_csv(url, yesterday, output_dir, failed_dir)
    if csv_filename:
        logger.info(f"CSV téléchargé avec succès: {csv_filename}")
    else:
        logger.warning(f"Échec du téléchargement pour la veille: {yesterday.strftime('%d/%m/%Y')}")


if __name__ == "__main__":
    main()