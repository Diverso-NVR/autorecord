from functools import wraps
import os
import pickle
from typing import List

from aiohttp import ClientSession
from aiofile import AIOFile, Reader
from loguru import logger

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from autorecord.core.settings import config


class GoogleBase:
    CREDS_PATH = config.google_creds_path

    def __init__(self):
        self._creds = None
        self._headers = {"Authorization": ""}
        self._client = ClientSession()

    def refresh_token(self) -> None:
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
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not self._creds or self._creds.expired:
            logger.info("Refresh google tokens")
            self.refresh_token()

        return await func(self, *args, **kwargs)

    return wrapper


class GoogleDrive(GoogleBase):
    UPLOAD_API_URL = "https://www.googleapis.com/upload/drive/v3"
    API_URL = "https://www.googleapis.com/drive/v3"
    SCOPES = config.google_drive_scopes
    TOKEN_PATH = config.google_drive_token_path

    @token_check
    async def upload(self, file_path: str, parent_id: str) -> str:
        logger.info(f"Started uploading {file_path}")

        meta_data = {"name": file_path.split("/")[-1], "parents": [parent_id]}

        resp = await self._client.post(
            f"{self.UPLOAD_API_URL}/files?uploadType=resumable",
            headers={**self._headers, **{"X-Upload-Content-Type": "video/mp4"}},
            json=meta_data,
            ssl=False,
        )
        session_url = resp.headers.get("Location")

        async with AIOFile(file_path, "rb") as afp:
            file_size = str(os.stat(file_path).st_size)
            reader = Reader(afp, chunk_size=256 * 1024 * 100)  # 25MB
            received_bytes_lower = 0
            async for chunk in reader:
                chunk_size = len(chunk)
                chunk_range = f"bytes {received_bytes_lower}-{received_bytes_lower + chunk_size - 1}"

                resp = await self._client.put(
                    session_url,
                    data=chunk,
                    headers={
                        "Content-Length": str(chunk_size),
                        "Content-Range": f"{chunk_range}/{file_size}",
                    },
                    ssl=False,
                )
                chunk_range = resp.headers.get("Range")

                try:
                    resp_json = await resp.json()
                    drive_file_id = resp_json["id"]
                except Exception:
                    pass

                if chunk_range is None:
                    break

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
        emails: List[str] = [],
    ) -> str:
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

            if not emails:
                acls = [{"type": "anyone", "role": "reader"}]
            else:
                acls = [
                    {"type": "user", "role": "reader", "emailAddress": email}
                    for email in emails
                ]
            resp_json = await resp.json()
            folder_id = resp_json["id"]
            for acl in acls:
                resp = await self._client.post(
                    f"{self.API_URL}/files/{folder_id}/permissions",
                    headers=self._headers,
                    json=acl,
                    ssl=False,
                )

        return folder_id

    @token_check
    async def get_folder_by_name(self, name: str) -> dict:
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
