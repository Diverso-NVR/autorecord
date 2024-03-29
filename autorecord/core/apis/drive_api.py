import os
import pickle
from typing import List
from functools import wraps
from asyncio import Semaphore

from loguru import logger
from aiohttp import ClientSession
from aiofile import AIOFile, Reader
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from autorecord.core.settings import config

GOOGLE_SEMAPHORE = Semaphore(config.google_semaphore)


class GoogleBase:
    """
    Класс базовой настройки любого гугл сервиса
    """

    CREDS_PATH = config.google_creds_path

    def __init__(self):
        self._creds = None
        self._headers = {"Authorization": ""}
        self._client = ClientSession()

    def refresh_token(self) -> None:
        """
        Пересоздаем токен и сохраняем в файл
        """
        creds = None

        if os.path.exists(self.TOKEN_PATH):
            with open(self.TOKEN_PATH, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.CREDS_PATH, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.TOKEN_PATH, "wb") as token:
                pickle.dump(creds, token)

        self._creds = creds
        self._headers["Authorization"] = f"Bearer {creds.token}"


def token_check(func):
    """
    Каждый час токен гугла протухает, поэтому нужно смотреть жив ли он ещё,
    если нет – создать новый токен
    """

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self._creds or self._creds.expired:
            logger.info("Refresh google tokens")
            self.refresh_token()

        return await func(self, *args, **kwargs)

    return wrapper


def semaphore(func):
    """
    Семафора, чтобы не грузить одновременно большое количество видео,
    иначе сеть будет провисать
    """

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        async with GOOGLE_SEMAPHORE:
            return await func(self, *args, **kwargs)

    return wrapper


class GoogleDrive(GoogleBase):
    """
    Класс работы с гугл драйвом
    """

    UPLOAD_API_URL = "https://www.googleapis.com/upload/drive/v3"
    API_URL = "https://www.googleapis.com/drive/v3"
    SCOPES = config.google_drive_scopes
    TOKEN_PATH = config.google_drive_token_path

    @token_check
    # @semaphore
    async def upload(self, file_path: str, parent_id: str) -> str:
        """
        Функция загрузки видео на диск.

        :param file_path: путь к файлу на сервере
        :param parent_id: id папки на гугл диске

        :return: id загруженного файла
        """
        logger.info(f"Started uploading {file_path}")

        meta_data = {"name": file_path.split("/")[-1], "parents": [parent_id]}

        # Создание канала передачи видео
        resp = await self._client.post(
            f"{self.UPLOAD_API_URL}/files?uploadType=resumable",
            headers={**self._headers, **{"X-Upload-Content-Type": "video/mp4"}},
            json=meta_data,
            ssl=False,
        )
        session_url = resp.headers.get("Location")

        async with AIOFile(file_path, "rb") as afp:
            # Асинхронное чтение файла по частям
            file_size = str(os.stat(file_path).st_size)
            reader = Reader(afp, chunk_size=256 * 1024 * 100)  # 25MB
            received_bytes_lower = 0
            async for chunk in reader:
                chunk_size = len(chunk)
                chunk_range = f"bytes {received_bytes_lower}-{received_bytes_lower + chunk_size - 1}"

                # Отправляем часть данных видео.
                # Гугл хочет в headers запроса флаги Content-Length и Content-Range
                # где Content-Length – размер отправляемых данных,
                # Content-Range – какой кусок данных шлём.
                resp = await self._client.put(
                    session_url,
                    data=chunk,
                    headers={
                        "Content-Length": str(chunk_size),
                        "Content-Range": f"{chunk_range}/{file_size}",
                    },
                    ssl=False,
                )
                # В ответ, если файл не до конца загружен гугл присылает тот же Content-Range в хедере Range.
                # Если файл загружен, то Range не будет
                chunk_range = resp.headers.get("Range")

                try:
                    resp_json = await resp.json()
                    drive_file_id = resp_json["id"]
                except Exception:
                    pass

                if chunk_range is None:
                    break

                # Из Range берём верхнее значение и по нему определяем следующий range
                _, bytes_data = chunk_range.split("=")
                _, received_bytes_lower = bytes_data.split("-")
                received_bytes_lower = int(received_bytes_lower) + 1

        logger.info(f"Uploaded {file_path}")

        return drive_file_id

    @token_check
    async def create_folder(
        self,
        folder_name: str,
        folder_parent_id: str = "",
    ) -> str:
        """
        Создаём папку на гугл диске и даём права на просмотр всем в интернете

        :param folder_name: имя папки
        :param folder_parent_id: id родительской папки. Если пустая строка – создаём в корне
        :return: id созданной папки
        """
        logger.info(
            f"Creating folder with name {folder_name} inside folder with id {folder_parent_id}"
        )

        meta_data = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if folder_parent_id:
            meta_data["parents"] = [folder_parent_id]

        resp = await self._client.post(
            f"{self.API_URL}/files",
            headers=self._headers,
            json=meta_data,
            ssl=False,
        )
        resp_json = await resp.json()
        folder_id = resp_json["id"]

        resp = await self._client.post(
            f"{self.API_URL}/files/{folder_id}/permissions",
            headers=self._headers,
            json={"type": "anyone", "role": "reader"},
            ssl=False,
        )

        return folder_id

    @token_check
    async def get_folder_by_name(self, name: str) -> dict:
        """
        Собираем папки на диске по имени

        :param name: имя папки
        :return: словарь id папки: список id родительских папок
        """
        logger.info(f"Getting the id of folder with name {name}")

        params = dict(
            fields="nextPageToken, files(name, id, parents)",
            q=f"mimeType='application/vnd.google-apps.folder'and name='{name}'",
            spaces="drive",
        )
        folders = []
        page_token = ""

        while page_token != False:
            resp = await self._client.get(
                f"{self.API_URL}/files?pageToken={page_token}",
                headers=self._headers,
                params=params,
                ssl=False,
            )
            resp_json = await resp.json()
            folders.extend(resp_json.get("files", []))
            page_token = resp_json.get("nextPageToken", False)

        return {folder["id"]: folder.get("parents", []) for folder in folders}
