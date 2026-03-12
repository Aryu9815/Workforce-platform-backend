# services/dashboard/base.py

from datetime import date

class DashboardContext:
    def __init__(self, user_id, start_date=None, end_date=None):
        self.user_id = user_id
        self.today = date.today()
        self.start_date = start_date or self.today.replace(day=1)
        self.end_date = end_date or self.today