from __future__ import print_function
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file as oauth_file, client, tools

# If modifying these scopes, delete the file token.json.
SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'


def save_to_gdrive(file, gdrive_dir):
    pass


def list_files(gdrive_dir="/", pageSize=10):
    """Shows basic usage of the Drive v3 API.

    Prints the names and ids of the first 10 files the user has access to.
    TODO How to make this transparent to the bot?
    """
    store = oauth_file.Storage('token.json')
    creds = store.get()
    print('creds:', creds)
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('../../credentials.json', SCOPES)
        creds = tools.run_flow(flow, store)
        print('Use credentials.json')
    service = build('drive', 'v3', http=creds.authorize(Http()))

    # Call the Drive v3 API
    results = service.files().list(
        pageSize=pageSize,
        fields="nextPageToken, files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(u'{0} ({1})'.format(item['name'], item['id']))


if __name__ == '__main__':
    gdrive_dir = 'line-listener'
    save_to_gdrive('../../test01.png', gdrive_dir)
    list_files()
