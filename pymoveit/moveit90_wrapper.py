import time
import logging

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

from pyodbc import connect as odbc_connect

logger = logging.getLogger('logger')


class MoveitConfig:
    def __init__(self, **kwargs):
        self.base_url = kwargs.pop('base_url')
        self.user_login = kwargs.pop('user_login')
        self.user_password = kwargs.pop('user_password')
        self.sql_server = kwargs.pop('sql_server')
        self.db_name = kwargs.pop('db_name')


conf: MoveitConfig


def configure(**kwargs):
    global conf
    conf = MoveitConfig(**kwargs)


class MoveitBrowser:
    def __init__(self, open_site: bool = False, login: bool = False):
        self.browser = self.__initialize_browser()
        if open_site:
            self.open_site()
        if login:
            self.login()

    @staticmethod
    def __initialize_browser():
        options = webdriver.ChromeOptions()
        prefs = {
            "safebrowsing.enabled": True,
            "profile.default_content_settings.popups": 0
        }
        options.add_experimental_option("prefs", prefs)
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    def get_element(self, element_id: str):
        return self.browser.find_element(By.ID, element_id)

    def fill_element(self, element_id: str, text: str):
        element = self.get_element(element_id)
        element.send_keys(text)

    def click_element(self, element_id: str):
        element = self.get_element(element_id)
        element.click()

    def open_site(self):
        self.browser.get(conf.base_url)
        time.sleep(1)
        self.click_element("details-button")
        time.sleep(1)
        self.click_element("proceed-link")
        time.sleep(1)

    def login(self):
        self.fill_element("form_username", conf.user_login)
        self.fill_element("form_password", conf.user_password)
        self.click_element("submit_button")

    def download_file(self, file_id: int):
        self.browser.get(f"{conf.base_url}/MOVEitDownload/arg01={file_id}!arg02=31!arg03=[OriginalFilename]!arg04=0!arg05=0/")

    def quit(self):
        self.browser.quit()


class MoveitDb:
    def __init__(self):
        driver = '{ODBC Driver 17 for SQL Server}'
        self.conn = f"Driver={driver};Server={conf.sql_server};Database={conf.db_name};Trusted_Connection=Yes;"
        with odbc_connect(self.conn) as conn:
            cursor = conn.cursor()
            cursor.execute("select 1 as result")
            for row in cursor.fetchall():
                break
        if row:
            if row.result != 1:
                logger.error(f'Moveit DMZ: Unexpected result SQL test connection')
        else:
            logger.error("Moveit DMZ: SQL test connection is failed")

    def get_folder_id(self, folder_path: str) -> int:
        query = f"select ID from dbo.folders where FolderPath = N'{folder_path}'"
        with odbc_connect(self.conn) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            for row in cursor.fetchall():
                break
        if row:
            if row.ID:
                return row.ID
            else:
                logger.error(f'Moveit DMZ: Unexpected result of the folder ID finding')
        else:
            logger.error(f"Moveit DMZ: No folder ID found for {folder_path}")

    def get_file_id(self, folder_path: str, file_name: str) -> int:
        folder_id = self.get_folder_id(folder_path)
        if folder_id:
            file_name = file_name.replace("'", "&#039;")
            query = f"select ID from dbo.files where FolderID = {folder_id} and OriginalFilename = N'{file_name}'"
            with odbc_connect(self.conn) as conn:
                cursor = conn.cursor()
                cursor.execute(query)
                for row in cursor.fetchall():
                    break
            if row:
                if row.ID:
                    return row.ID
                else:
                    logger.error(f'Moveit DMZ: Unexpected result of the file ID finding')
            else:
                logger.error("Moveit DMZ: No result during the file ID finding")
