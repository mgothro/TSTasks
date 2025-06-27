from dbconn import execute_query
import calendar
from datetime import datetime, timedelta
from flask import flash

class Schedule:
    def __init__(self, task_id=None, frequency=None, interval=None, end_date=None, next_run=None, email_subject=None):
        self.task_id = task_id
        self.frequency = frequency
        self.interval = interval
        self.end_date = end_date
        self.next_run = next_run
        self.email_subject = email_subject

    def save(self):
        if hasattr(self, 'id'):
            query = '''
                UPDATE [task].[Schedule]
                SET task_id = ?, created_at = ?, deleted_at = ?, frequency = ?, interval = ?,
                    end_date = ?, next_run = ?, last_run = ?, email_subject = ?
                WHERE id = ?
            '''
            params = (self.task_id, self.created_at, self.deleted_at, self.frequency, self.interval,
                      self.end_date, self.next_run, self.last_run, self.email_subject, self.id)
            execute_query(query, params)
            flash(f'Schedule (ID: {self.id}) saved successfully!')
        else:
            query = '''
                INSERT INTO [task].[Schedule] (task_id, frequency, interval, end_date, next_run, email_subject)
                VALUES (?, ?, ?, ?, ?, ?);
                SELECT SCOPE_IDENTITY();
            '''
            params = (self.task_id, self.frequency, self.interval,
                      self.end_date, self.next_run, self.email_subject)
            result = execute_query(query, params, fetch_one=True)
            self.id = result[0] if result else None
            flash(f'Schedule (ID: {self.id}) created successfully!')

    @classmethod
    def get_by_id(cls, schedule_id):
        query = 'SELECT * FROM [task].[Schedule] WHERE id = ?'
        row = execute_query(query, (schedule_id,), fetch_one=True)
        if row:
            obj = cls()
            obj.__dict__.update(cls.row_to_dict(cls, row))
            return obj
        return None

    @classmethod
    def get_all(cls):
        query = 'SELECT * FROM [task].[Schedule]'
        rows = execute_query(query, fetch_all=True)
        schedules = []
        for row in rows:
            obj = cls()
            obj.__dict__.update(cls.row_to_dict(cls, row))
            schedules.append(obj)
        return schedules

    @classmethod
    def get_pending(cls):
        query = '''
            SELECT * FROM [task].[Schedule]
            WHERE next_run < GETDATE() AND ISNULL(end_date, next_run) >= next_run
        '''
        rows = execute_query(query, fetch_all=True)
        schedules = []
        for row in rows:
            obj = cls()
            obj.__dict__.update(cls.row_to_dict(cls, row))
            schedules.append(obj)
        return schedules

    @classmethod
    def get_by_task_id(cls, task_id):
        query = 'SELECT * FROM [task].[Schedule] WHERE task_id = ? ORDER BY id DESC'
        rows = execute_query(query, (task_id,), fetch_all=True)
        schedules = []
        for row in rows:
            obj = cls()
            obj.__dict__.update(cls.row_to_dict(cls, row))
            schedules.append(obj)
        return schedules

    def delete(self):
        if hasattr(self, 'id'):
            query = 'DELETE FROM [task].[Schedule] WHERE id = ?'
            execute_query(query, (self.id,))
            del self.id

    def advance(self):
        try:
            current_time = datetime.now()
            frequency = (self.frequency or '').lower()

            while self.next_run and self.next_run < current_time:
                if frequency == 'month':
                    year = self.next_run.year + (self.next_run.month // 12)
                    month = (self.next_run.month % 12) + int(self.interval)
                    last_day = calendar.monthrange(year, month)[1]
                    day = min(self.next_run.day, last_day)
                    next_run = datetime(year, month, day, self.next_run.hour, self.next_run.minute, self.next_run.second)
                elif frequency == 'day':
                    next_run = self.next_run + timedelta(days=int(self.interval))
                else:
                    raise ValueError(f"Unhandled frequency: {self.frequency}")
                
                self.next_run = next_run

            query = '''
                UPDATE s
                SET s.next_run = ?, s.last_run = ?
                FROM task.schedule s
                WHERE s.id = ?
            '''
            params = (self.next_run, current_time, self.id)
            execute_query(query, params)

        except Exception as e:
            print(f"Error in advance(): {e}")

    @staticmethod
    def row_to_dict(cls, row):
        return {desc[0]: val for desc, val in zip(cls.__annotations__.items(), row)}
