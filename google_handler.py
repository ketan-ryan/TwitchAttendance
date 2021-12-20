from google.oauth2 import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
import os


SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']


class GoogleHandler():
    channel = ''
    creds = None
    id = ''

    def __init__(self, chan):
        """Initialize and authenticate with Google API"""
        self.channel = chan
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first time.
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())


    def get_sheet(self):
        """Gets list of all spreadsheets in the drive account
        If it finds the desired streamer's spreadsheet, log the spreadsheet ID
        If not, we need to create the sheet"""
        try:
            service = build('drive', 'v3', credentials=self.creds)
            # Get list of all spreadsheets
            res = service.files().list(q="mimeType='application/vnd.google-apps.spreadsheet'", fields='nextPageToken, files(id, name)').execute()
            items = res.get('files', [])

            # Get spreadsheet id if it exists
            names = [k['name'] for k in items]
            if self.channel in names:
                print(items[names.index(self.channel)]['id'])
            # If not, we need to create it
            else:
                self.create_sheet()
        except HttpError as e:
            print(e)


    def create_sheet():
        pass


if __name__ == '__main__':
    gh = GoogleHandler('atrioc')
    gh.get_sheet()
