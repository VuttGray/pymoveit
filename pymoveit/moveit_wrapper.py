import requests
from urllib3 import disable_warnings
from logging import getLogger

logger = getLogger('glogger')


class MoveitConfig:
    def __init__(self, **kwargs):
        self.base_api_url = kwargs.pop('base_api_url')
        self.user_login = kwargs.pop('user_login')
        self.user_password = kwargs.pop('user_password')


conf: MoveitConfig


def configure(**kwargs):
    global conf
    conf = MoveitConfig(**kwargs)


class MoveitApi:
    def __init__(self):
        disable_warnings()
        self.token = ""
        self.authorize()

    @staticmethod
    def get_url(url: str, parameters: str = "") -> str:
        return f"{conf.base_api_url}/{url}" + (f'?{parameters}' if parameters else '')

    def authorize(self):
        logger.info("Auth starting")
        headers = {"accept": "application/json",
                   "Content-Type": "application/x-www-form-urlencoded"}
        data = {'grant_type': 'password',
                'username': conf.user_login,
                'password': conf.user_password}
        url = self.get_url('token')
        api_response = requests.post(url,
                                     headers=headers,
                                     data=data,
                                     verify=False)
        if api_response.status_code == 200:
            self.token = api_response.json().get('access_token')
            if self.token:
                logger.info(f"MOVEit API Auth token: {self.token}")
            else:
                logger.error("MOVEit API Auth error: no access token in the response")
                logger.info(api_response.json())
                exit(0)
        else:
            logger.error(f'MOVEit API Auth error: {api_response.status_code}: {api_response.text}')

    def __get(self, url: str, allow_redirects: bool=False) -> dict:
        headers = {"accept": "application/json",
                   "Authorization": "Bearer " + self.token}
        api_response = requests.get(url,
                                    headers=headers,
                                    verify=False,
                                    allow_redirects=allow_redirects)
        if api_response.status_code == 401:
            return self.__get(url, allow_redirects)
        if api_response.status_code != 200:
            logger.error(f"HTTP GET error: {api_response.status_code}: {api_response.text}")
        else:
            return api_response.json()

    def __get_items(self, entity_url: str, page: int = None, per_page: int = None) -> list:
        parameters = f"page={page}" if page else ""
        parameters += f"perPage={per_page}" if per_page else ""
        url = self.get_url(entity_url, parameters)
        response = self.__get(url)
        return response.get("items")

    def get_folder(self, folder_id: int):
        url = self.get_url(f'folders/{folder_id}')
        return self.__get(url)

    def get_folders(self, page: int = None, per_page: int = None):
        return self.__get_items('folders', page, per_page)

    def get_root_folder_id(self) -> int:
        for f in self.get_folders():
            if f.get("folderType") == "Root":
                return int(f.get("id"))

    def get_subfolders(self, folder_id: int, page: int = None, per_page: int = None):
        return self.__get_items(f'folders/{folder_id}/subfolders', page, per_page)

    def find_subfolder(self, folder_id: int, name: str):
        for f in self.get_subfolders(folder_id):
            if f.get("name") == name:
                return f

    def find_folder(self, start_folder_id: int = 0, folder_path: str = "", name: str = "") -> int:
        start_folder_id = start_folder_id if start_folder_id else self.get_root_folder_id()
        folder_path = folder_path if folder_path else name
        folder_path = folder_path[1:] if folder_path.startswith('/') else folder_path
        for name in folder_path.split('/'):
            subfolder_id = 0
            for f in self.get_subfolders(start_folder_id, per_page=100):
                if f["name"] == name:
                    subfolder_id = int(f["id"])
                    break
            if subfolder_id:
                start_folder_id = subfolder_id  # Next cycle step - find the next sub folder in the tree
            else:
                return 0
        return start_folder_id

    def get_files(self, folder_id: int, page: int = None, per_page: int = None):
        return self.__get_items(f'folders/{folder_id}/files', page, per_page)

    def find_file(self, folder_id: int, name: str) -> int:
        for f in self.get_files(folder_id):
            if f["name"] == name:
                return int(f["id"])
        return 0

    def add_folder(self, parent_id: int, name: str):
        url = self.get_url(f"folders/{parent_id}/subfolders")
        data = '{"inheritPermissions": "None", "name": "' + name + '"}'
        headers = {"accept": "application/json",
                   "Content-Type": "application/json",
                   "Authorization": "Bearer " + self.token}
        api_response = requests.post(url, data=data, headers=headers, verify=False)
        if api_response.status_code == 401:
            logger.error(f'Error: {api_response.status_code}: {api_response.text}')
            return self.add_folder(parent_id, name)
        if api_response.status_code != 201:
            logger.error(f'Error: {api_response.status_code}: {api_response.text}')

    def add_file(self, parent_id: int, file_path: str):
        url = self.get_url(f"folders/{parent_id}/files")
        files = {'file': open(file_path, 'rb')}
        headers = {"accept": "application/json",
                   "Authorization": "Bearer " + self.token}
        api_response = requests.post(url, files=files, headers=headers, verify=False)
        if api_response.status_code == 401:
            logger.error(f'Error: {api_response.status_code}: {api_response.text}')
            return self.add_file(parent_id, file_path)
        if api_response.status_code == 201:
            logger.info(f'File {file_path} uploaded')
        else:
            logger.error(f'Error: {api_response.status_code}: {api_response.text}')

    def file_exists(self, file_name: str, folder_path: str) -> bool:
        folder_id = self.find_folder(folder_path=folder_path)
        if folder_id:
            file_id = self.find_file(folder_id, file_name)
            if file_id:
                logger.info(f"MOVEit API: {file_name} is find in {folder_path}")
                return True
