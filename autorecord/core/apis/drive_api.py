from __future__ import print_function

import logging
import os.path
import os
import json
import pickle
import requests
from threading import RLock

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

lock = RLock()

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
API_URL = 'https://www.googleapis.com/upload/drive/v3'
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {creds.token}"
}


def token_check(func):
    def wrapper(*args, **kwargs):
        with lock:
            creds_generate()
            HEADERS["Authorization"] = f"Bearer {creds.token}"
            return func(*args, **kwargs)

    return wrapper


drive_service = build('drive', 'v3', credentials=creds)

logger = logging.getLogger('autorecord_logger')


@token_check
def upload_req(file_path: str, folder_id: str) -> str:
    meta_data = {
        "name": file_path.split('/')[-1],
        "parents": [folder_id]
    }

    res = requests.post(f'{API_URL}/files?uploadType=resumable',
                        headers={**HEADERS,
                                 **{"X-Upload-Content-Type": "video/mp4"}},
                        json=meta_data)

    file = open(file_path, 'rb')

    session_url = res.headers.get('Location')
    res = requests.put(session_url, data=file.read(),
                       headers={"Content-Length": str(os.stat(file_path).st_size)})

    os.remove(file_path)

    logger.info(
        f'Uploaded {file_path}')


def upload(file_name: str, folder_id: str) -> str:
    """
    Upload file "filename" on drive folder 'folder_id'
    """
    media = MediaFileUpload(
        file_name, mimetype="video/mp4", resumable=True)
    file_data = {
        "name": file_name.split('/')[-1],
        "parents": [folder_id]
    }
    file = drive_service.files().create(
        body=file_data, media_body=media).execute()

    os.remove(file_name)

    return file.get('id')


def create_folder(folder_name: str, folder_parent_id: str = '') -> str:
    """
    Creates folder in format: 'folder_name'
    """
    with lock:
        logger.info(
            f'Creating folder with name {folder_name} inside folder with id {folder_parent_id}')

        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if folder_parent_id:
            folder_metadata['parents'] = [folder_parent_id]
        folder = drive_service.files().create(body=folder_metadata,
                                              fields='id').execute()

        new_perm = {
            'type': 'anyone',
            'role': 'reader'
        }

        drive_service.permissions().create(
            fileId=folder['id'], body=new_perm).execute()

        return "https://drive.google.com/drive/u/1/folders/" + folder['id']


def get_folder_by_name(name: str) -> dict:
    with lock:
        logger.info(f'Getting the id of folder with name {name}')

        page_token = None

        while True:
            response = drive_service.files().list(q=f"mimeType='application/vnd.google-apps.folder'"
                                                    f"and name='{name}'",
                                                    spaces='drive',
                                                    fields='nextPageToken, files(name, id, parents)',
                                                    pageToken=page_token).execute()
            page_token = response.get('nextPageToken', None)
            print(page_token)

            if page_token is None:
                break

        return {folder['id']: folder.get('parents', [''])[0] for folder in response['files']}
