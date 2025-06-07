import os
import time
import logging
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# -----------------------------------------------------------------------------------
# Configuration du logging
# -----------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('asfim_performance_scraper_selenium.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def setup_driver(download_dir):
    """
    Configure le navigateur Chrome avec Selenium et définit le répertoire de téléchargement.

    Args:
        download_dir (str): Chemin absolu du répertoire de téléchargement.

    Returns:
        WebDriver: Instance du navigateur Chrome configuré.
    """
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Décommentez si vous voulez le mode sans interface
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Préférences pour le téléchargement
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Utiliser ChromeDriverManager pour gérer automatiquement la version du driver
    service = ChromeService(executable_path=ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def get_download_links(driver):
    """
    Récupère tous les liens de téléchargement (.xlsx) présents sur la page actuelle.

    Args:
        driver (WebDriver): Instance du driver.

    Returns:
        set: Ensemble d’URLs à télécharger.
    """
    links = set()
    # On recherche les <a> ayant la classe correspondant aux liens de téléchargement
    download_elements = driver.find_elements(
        By.CSS_SELECTOR,
        "a.text-blue-600.hover\\:text-blue-900.flex.items-center"
    )
    for element in download_elements:
        href = element.get_attribute("href")
        if href and href.lower().endswith(".xlsx"):
            links.add(href)
    return links


def download_asfim_performance_files(
        base_url="https://asfim.ma/publications/tableaux-des-performances/",
        output_dir="asfim_performance_xlsx"
):
    """
    Scrape et télécharge tous les fichiers Excel de la liste ASFIM (quotidiens et hebdomadaires),
    en gérant simplement la pagination jusqu'à ce que le bouton 'Suivant' soit désactivé ou absent.

    Args:
        base_url (str): URL de la page listant les performances.
        output_dir (str): Répertoire local pour sauvegarder les fichiers téléchargés.
    """
    # --- Création du répertoire local s’il n’existe pas ---
    absolute_output_dir = os.path.abspath(output_dir)
    if not os.path.exists(absolute_output_dir):
        os.makedirs(absolute_output_dir)
        logger.info(f"Répertoire {absolute_output_dir} créé.")

    # --- Initialisation du driver Selenium ---
    driver = setup_driver(absolute_output_dir)
    wait = WebDriverWait(driver, 10)
    actions = ActionChains(driver)

    try:
        # 1. Accéder à la page principale
        logger.info(f"Accès à la page : {base_url}")
        driver.get(base_url)

        # 2. Attendre le chargement initial du body
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)  # Petit sleep pour s’assurer que le JS est totalement chargé

        # 3. Tenter de passer à 100 lignes par page si ce select est présent (sinon on ignore)
        try:
            per_page_select = driver.find_element(
                By.XPATH,
                "/html/body/main/main/section[2]/div/div[2]/div[4]/div[2]/div[1]/select"
            )
            for option in per_page_select.find_elements(By.TAG_NAME, "option"):
                if option.text.strip() == "100":
                    option.click()
                    time.sleep(2)  # Attendre que la page se recharge
                    logger.info("Nombre de lignes par page défini à 100.")
                    break
        except Exception as e:
            logger.warning(f"Impossible de modifier le nombre de lignes par page : {e}")

        # --- Boucle principale de téléchargement + pagination ---
        page_num = 1
        total_files_downloaded = 0
        while True:
            logger.info(f"Début du traitement de la page {page_num}...")

            # a) Récupérer et télécharger les liens .xlsx de la page courante
            current_links = get_download_links(driver)
            logger.info(f"Nombre de liens .xlsx trouvés sur la page {page_num} : {len(current_links)}")
            logger.debug(f"Liens trouvés sur la page {page_num} : {current_links}")

            if not current_links:
                logger.warning(f"Aucun lien .xlsx trouvé sur la page {page_num}.")
            else:
                page_files_downloaded = 0
                for href in current_links:
                    try:
                        filename = urllib.parse.unquote(href.split("/")[-1])
                        expected_filepath = os.path.join(absolute_output_dir, filename)

                        # Si déjà téléchargé, on ignore
                        if os.path.exists(expected_filepath):
                            logger.info(f"Fichier déjà présent sur la page {page_num} : {filename}")
                            continue

                        # Cliquer sur le lien pour lancer le téléchargement
                        logger.info(f"Téléchargement de {filename} sur la page {page_num}...")
                        link_elem = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a[href='{href}']")))

                        # Défilement vers l'élément pour le rendre cliquable
                        actions.move_to_element(link_elem).perform()
                        time.sleep(2)  # Augmenter le délai pour éviter les erreurs d'interception

                        # Tentative de clic natif
                        try:
                            link_elem.click()
                        except Exception as e:
                            # Si le clic natif échoue, utiliser un clic JavaScript
                            logger.warning(
                                f"Clic natif échoué pour {filename} sur la page {page_num}, tentative avec JavaScript : {e}")
                            driver.execute_script("arguments[0].click();", link_elem)

                        # Attendre que le fichier soit présent (timeout 20 sec)
                        timeout = 20
                        start_time = time.time()
                        while not os.path.exists(expected_filepath) and (time.time() - start_time) < timeout:
                            time.sleep(1)

                        if os.path.exists(expected_filepath):
                            logger.info(f"Fichier téléchargé avec succès sur la page {page_num} : {filename}")
                            page_files_downloaded += 1
                            total_files_downloaded += 1
                        else:
                            logger.warning(
                                f"Échec du téléchargement de {filename} sur la page {page_num} après {timeout} secondes.")
                    except Exception as e:
                        logger.error(f"Erreur durant le téléchargement de {href} sur la page {page_num} : {e}")
                        continue
                logger.info(f"Nombre de nouveaux fichiers téléchargés sur la page {page_num} : {page_files_downloaded}")

            # b) Tenter de cliquer sur “Suivant” pour passer à la page suivante
            try:
                # Attendre que le bloc de pagination soit présent
                wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR,
                     "body > main > main > section.w-full.bg-white.py-12.md\\:py-16 "
                     "> div > div.w-full.font-poppins > div.mt-4.flex.flex-col.md\\:flex-row.justify-between.items-center")
                ))
                # Sélecteur CSS pointé pour le bouton “Suivant” (3ème bouton)
                next_button = driver.find_element(
                    By.CSS_SELECTOR,
                    "body > main > main > section.w-full.bg-white.py-12.md\\:py-16 "
                    "> div > div.w-full.font-poppins > div.mt-4.flex.flex-col.md\\:flex-row.justify-between.items-center "
                    "> div.flex.items-center.space-x-4.text-black > div:nth-child(2) > button:nth-child(3)"
                )

                # Si le bouton “Suivant” est désactivé (attribut disabled ou non cliquable), on s’arrête
                if next_button.get_attribute("disabled") is not None or not next_button.is_enabled():
                    logger.info("Bouton 'Suivant' désactivé. Fin de la pagination.")
                    break

                # Sinon, cliquer dessus
                logger.info("Clic sur le bouton 'Suivant' pour passer à la page suivante...")
                wait.until(EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "body > main > main > section.w-full.bg-white.py-12.md\\:py-16 "
                    "> div > div.w-full.font-poppins > div.mt-4.flex.flex-col.md\\:flex-row.justify-between.items-center "
                    "> div.flex.items-center.space-x-4.text-black > div:nth-child(2) > button:nth-child(3)"
                )))
                next_button.click()

                # Attendre quelques secondes le temps que la nouvelle page charge
                time.sleep(3)
                page_num += 1
                continue  # revenir au début de la boucle pour traiter la nouvelle page

            except Exception as e:
                logger.info(f"Pas de bouton 'Suivant' cliquable ou erreur détectée : {e}. Fin de la pagination.")
                break

    except Exception as e:
        logger.error(f"Erreur générale lors du scraping : {e}")

    finally:
        logger.info(f"Total des nouveaux fichiers téléchargés : {total_files_downloaded}")
        driver.quit()
        logger.info("Navigateur fermé.")


if __name__ == "__main__":
    download_asfim_performance_files()