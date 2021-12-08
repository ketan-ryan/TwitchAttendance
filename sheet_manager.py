from tqdm import tqdm
import openpyxl
import datetime
import os

class SheetManager:
    wb = None
    current_sheet = None
    need_list = False
    day = datetime.datetime.today().strftime('%-d')
    name = None
    total_entries = 2
    all_followers = []


    def __init__(self, streamer_name) -> None:
        self.name = streamer_name
        self.wb = openpyxl.load_workbook(f'{streamer_name}.xlsx')

        self.current_sheet = self.wb.active
        month_year = datetime.datetime.today().strftime('%m-%Y')
        sheet_exists = False

        for idx, s in enumerate(self.wb.sheetnames):
            if s == month_year:
                self.current_sheet = self.wb.worksheets[idx]
                sheet_exists = True

        if not sheet_exists:
            self.wb.active = self.wb.create_sheet(month_year)
            self.current_sheet = self.wb.active

            self.current_sheet['A1'] = 'Chatter'
            self.current_sheet.cell(row=1, column=int(self.day) + 1).value = datetime.datetime.today().strftime('%-d/%-m')
            self.need_list = True


    def need_update(self):
        return self.need_list


    def write_list(self, chatter_names):
        for idx, name in enumerate(chatter_names):
            self.current_sheet.cell(self.total_entries + idx, column=1).value = name
        self.total_entries = self.total_entries + len(chatter_names)
        print(self.total_entries)


    def get_followers(self):
        if(len(self.all_followers) == 0):
            for i in range(2, self.current_sheet.max_row):
                self.all_followers.append(str(self.current_sheet.cell(i, 1).value))
        self.all_followers = [str.lower(follower) for follower in self.all_followers]
        return self.all_followers


    def update_attendance(self, username, val):
        try:
            idx = self.all_followers.index(username)
        except ValueError:
            return
        col = int(self.day)
        if val == 'Lurking' and self.current_sheet.cell(idx + 2, col).value == '':
            self.current_sheet.cell(idx + 2, col).value = val
        elif val == 'Present':
            self.current_sheet.cell(idx + 2, col).value = val


    def close(self):
        self.wb.save(f'{self.name}.xlsx')
