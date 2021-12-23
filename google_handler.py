from google.oauth2 import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
import os

from sheet_manager import SheetManager


SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']


class GoogleHandler():
    sheet_title = ''
    sheet_id = None
    service = None
    channel = ''
    creds = None
    id = ''

    def __init__(self, chan, title):
        """Initialize and authenticate with Google API"""
        self.channel = chan
        self.sheet_title = title
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
        try:
            self.service = build('sheets', 'v4', credentials=self.creds)
        except HttpError as e:
            print('Unable to connect to Sheets API')


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
                self.id = items[names.index(self.channel)]['id']
                return True
            # If not, we need to create it
            else:
                self.create_sheet()
        except HttpError as e:
            print(e)


    def create_sheet(self):
        """Creates a new spreadsheet titled after our streamer"""
        spreadsheet = {
            'properties': {
                'title': self.channel
            }
        }
        spreadsheet = self.service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        self.id = spreadsheet.get('spreadsheetId')


    def update_sheet(self, cell):
        """
        If a sheet does not exist already with the current month-year, create it
        Takes an openpyxl cell object, updates the corresponding cell in the google sheets
        Copies over color (slightly off for some reason), location, and value of a cell
        """
        sheet_metadata = self.service.spreadsheets().get(spreadsheetId=self.id).execute()
        sheets = sheet_metadata.get('sheets', '')
        titles = [s['properties']['title'] for s in sheets]
        if self.sheet_title not in titles:
            body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': self.sheet_title
                        }
                    }
                }]
            }
            self.service.spreadsheets().batchUpdate(spreadsheetId=self.id, body=body).execute()

        for sheet in sheets:
            if sheet['properties']['title'] == self.sheet_title:
                self.sheet_id = sheet['properties']['sheetId']
                break

        val = cell.value
        row = cell.row
        col = cell.col_idx
        hex_color = cell.fill.fgColor.index
        hex_color = hex_color[2:] # strip leading zeroes
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        # Based off this SO response: https://stackoverflow.com/a/62632799
        batch_update_body = {
            "requests": [
                {
                    "updateCells": {
                        "range": {
                            "sheetId": self.sheet_id,
                            "startRowIndex": row - 1,
                            "endRowIndex": row,
                            "startColumnIndex": col - 1,
                            "endColumnIndex": col
                        },
                        "rows": [
                            {
                                "values": [
                                    {
                                        "userEnteredValue": {
                                            "stringValue": val
                                        }
                                    }
                                ]
                            }
                        ],
                        "fields": "userEnteredValue"
                    }
                },
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": self.sheet_id,
                            "startRowIndex": row - 1,
                            "endRowIndex": row,
                            "startColumnIndex": col - 1,
                            "endColumnIndex": col
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0 if rgb[0] == 0 else 255.0 / rgb[0],
                                    "green": 0 if rgb[1] == 0 else 255.0 / rgb[1],
                                    "blue": 0 if rgb[2] == 0 else 255.0 / rgb[2]
                                }
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                }
            ]
        }
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.id, body=batch_update_body).execute()


    def get_cell(self, cell):
        """
        Input: A cell in A1 format
        Returns: The contents of the cell
        """
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.id, range=f'{self.sheet_title}!{(cell)}').execute()
        return result.get('values', [])


if __name__ == '__main__':
    gh = GoogleHandler('atrioc', '12-2021')
    sh = SheetManager('atrioc')
    gh.get_sheet()
    gh.update_sheet(sh.get_cell(2, 20))
    print(gh.get_cell('T2'))
