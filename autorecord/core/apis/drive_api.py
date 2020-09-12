from __future__ import print_function

import logging
import os.path
import os
import json
import pickle
import requests
from datetime import datetime, timedelta

import asyncio
from aiohttp import ClientSession
from aiofile import AIOFile, Reader
import concurrent.futures

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = 'https://www.googleapis.com/auth/drive'
"""
Setting up drive
"""
creds = None
TOKEN_PATH = '/autorecord/creds/tokenDrive.pickle'
CREDS_PATH = '/autorecord/creds/credentials.json'


# TODO: try to do it DRY
def creds_generate():
    global creds
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)


creds_generate()
UPLOAD_API_URL = 'https://www.googleapis.com/upload/drive/v3'
API_URL = 'https://www.googleapis.com/drive/v3'
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {creds.token}"
}

logger = logging.getLogger('autorecord_logger')


def token_check(func):
    async def wrapper(*args, **kwargs):
        if creds.expiry + timedelta(hours=3) <= datetime.now():  # refresh token
            logger.info("Recreating google creds")

            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await loop.run_in_executor(
                    pool, creds_generate)

            HEADERS["Authorization"] = f"Bearer {creds.token}"
        return await func(*args, **kwargs)

    return wrapper


@token_check
async def upload(file_path: str, folder_id: str) -> str:
    meta_data = {
        "name": file_path.split('/')[-1],
        "parents": [folder_id]
    }

    async with ClientSession() as session:
        async with session.post(f'{UPLOAD_API_URL}/files?uploadType=resumable',
                                headers={**HEADERS,
                                         **{"X-Upload-Content-Type": "video/mp4"}},
                                json=meta_data,
                                ssl=False) as resp:
            session_url = resp.headers.get('Location')

        async with AIOFile(file_path, 'rb') as afp:
            file_size = str(os.stat(file_path).st_size)
            reader = Reader(afp, chunk_size=256 * 1024 * 20)  # 5MB
            chunk_range = f"bytes 0-{256 * 1024 * 20 - 1}"
            async for chunk in reader:
                chunk_size = len(chunk)
                logger.info(f'{chunk_size = }')
                async with session.put(session_url, data=chunk, ssl=False,
                                       headers={"Content-Length": str(chunk_size),
                                                "Content-Range": f"{chunk_range}/{file_size}"}) as resp:
                    # Gives bytes=.../...
                    chunk_range = resp.headers.get('Range')
                    # But we need without '='
                    chunk_range = ' '.join(chunk_range.split('='))
                    logger.info(f'{resp.status = }')
                    logger.info(f'{await resp.text() = }')
                    logger.info(f'{chunk_range = }')

    os.remove(file_path)

    logger.info(
        f'Uploaded {file_path}')


@token_check
async def create_folder(folder_name: str, folder_parent_id: str = '') -> str:
    """
    Creates folder in format: 'folder_name'
    """
    logger.info(
        f'Creating folder with name {folder_name} inside folder with id {folder_parent_id}')

    meta_data = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if folder_parent_id:
        meta_data['parents'] = [folder_parent_id]

    async with ClientSession() as session:
        async with session.post(f'{API_URL}/files',
                                headers=HEADERS,
                                json=meta_data,
                                ssl=False) as resp:

            resp_json = await resp.json()
            folder_id = resp_json['id']

        new_perm = {
            'type': 'anyone',
            'role': 'reader'
        }

        async with session.post(f'{API_URL}/files/{folder_id}/permissions',
                                headers=HEADERS,
                                json=new_perm,
                                ssl=False) as resp:
            pass

    return f"https://drive.google.com/drive/u/1/folders/{folder_id}"


@token_check
async def get_folder_by_name(name: str) -> dict:
    logger.info(f'Getting the id of folder with name {name}')

    params = dict(
        fields='nextPageToken, files(name, id, parents)',
        q=f"mimeType='application/vnd.google-apps.folder'and name='{name}'",
        spaces='drive'
    )
    folders = []
    page_token = ''

    async with ClientSession() as session:
        while page_token != False:
            async with session.get(f'{API_URL}/files?pageToken={page_token}',
                                   headers=HEADERS, params=params,
                                   ssl=False) as resp:
                resp_json = await resp.json()
                folders.extend(resp_json.get('files', []))
                page_token = resp_json.get('nextPageToken', False)

    return {folder['id']: folder.get('parents', [''])[0] for folder in folders}
