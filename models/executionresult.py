from dbconn import execute_query

class ExecutionResult:
    
    def __init__(self, id=None, task_id=None, schedule_id=None, start_time=None, end_time=None, status=None, error_message=None):
        self.id = id
        self.task_id = task_id
        self.schedule_id = schedule_id
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.error_message = error_message

    def save(self):
        if self.id:
            # Update
            query = """
                UPDATE task.ExecutionResult
                SET task_id = ?, schedule_id = ?, start_time = ?, end_time = ?, status = ?, error_message = ?
                WHERE id = ?
            """
            params = (self.task_id, self.schedule_id, self.start_time, self.end_time, self.status, self.error_message, self.id)
            execute_query(query, params)
        else:
            # Insert
            query = """
                INSERT INTO task.ExecutionResult (task_id, schedule_id, start_time, end_time, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?);
                SELECT SCOPE_IDENTITY();
            """
            params = (self.task_id, self.schedule_id, self.start_time, self.end_time, self.status, self.error_message)
            result = execute_query(query, params, fetch_one=True)
            self.id = result[0] if result else None

    @classmethod
    def get_by_task_id(cls, task_id):
        query = "SELECT * FROM task.ExecutionResult WHERE task_id = ? ORDER BY id DESC"
        rows = execute_query(query, (task_id,), fetch_all=True)
        return [cls(*row) for row in rows] if rows else []

    @classmethod
    def get_by_schedule_id(cls, schedule_id):
        query = "SELECT * FROM task.ExecutionResult WHERE schedule_id = ? ORDER BY id DESC"
        rows = execute_query(query, (schedule_id,), fetch_all=True)
        return [cls(*row) for row in rows] if rows else []

    def get_latest_by_task_id(self, task_id):
        query = """
            SELECT TOP 1 * 
            FROM task.ExecutionResult 
            WHERE task_id = ?
            ORDER BY start_time DESC
        """
        row = execute_query(query, (task_id,), fetch_one=True)
        return ExecutionResult(*row) if row else None
