from dbconn import execute_query
from flask import flash

class EmailRecipient(object):
    def __init__(self, id = None, schedule_id = None, email = None) -> None:
        self.id = id
        self.schedule_id = schedule_id
        self.email = email

    def save(self):
        # Check if the object has an ID (indicating it already exists in the database)
        if self.id:
            # Update an existing record
            query = """
            UPDATE [task].[EmailRecipient]
            SET schedule_id = ?, email = ?
            WHERE id = ?
            """
            execute_query(query, (self.schedule_id, self.email, self.id))
        else:
            # Insert a new record
            query = """
            INSERT INTO [task].[EmailRecipient] (schedule_id, email)
            VALUES (?, ?)

            select @@IDENTITY as id
            """
            self.id = execute_query('SELECT @@IDENTITY')

        flash('Email recipients saved successfully!')
        
    def new_recipient(schedule_id, emails):
        for recipient in emails:
            query = """
            INSERT INTO [task].[EmailRecipient] (schedule_id, email)
            VALUES (?, ?)
            """
            execute_query(query, (schedule_id, recipient))
        
    def delete_recipient(schedule_id, email):
        query = """
        DELETE FROM [task].[EmailRecipient]
        WHERE schedule_id = ? 
        AND email = ?
		"""
        execute_query(query, (schedule_id, email))

        flash('Email recipient deleted successfully')

    def get_recipients_for_schedule(self, schedule_id):
        query = "SELECT * FROM task.EmailRecipient WHERE schedule_id = ?"
        results = execute_query(query, (schedule_id))

        recipients = []
        for row in results:
            email_recipient = EmailRecipient(id=row['id'], schedule_id=row['schedule_id'], email=row['email'])
            recipients.append(email_recipient)

        return recipients