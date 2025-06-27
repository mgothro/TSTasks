from inspect import getmembers, isclass
import importlib
from abc import ABC, abstractmethod
from flask import flash
from dbconn import execute_query
from models.sitegroup import SiteGroup

class Task(ABC):
    def __init__(self):
        self.send_email = True
        self.email_body = ' '  # Avoid PostMark rejection
        self.error_messages = []

    @property
    def email_body(self):
        return self._email_body

    @email_body.setter
    def email_body(self, email_body):
        self._email_body = email_body

    @abstractmethod
    def run(self):
        pass

    @classmethod
    def get_task_classes(cls):
        return {k: v for k, v in getmembers(importlib.import_module('tasks'), isclass)}

    def save(self):
        if hasattr(self, 'id'):
            query = '''
                UPDATE [task].[Task]
                SET sitegroup_id = ?, name = ?, description = ?, task_class = ?
                WHERE id = ?
            '''
            params = (self.sitegroup_id, self.name, self.description, self.task_class, self.id)
            execute_query(query, params)
            flash(f'Task (ID: {self.id}) saved successfully!')
        else:
            query = '''
                INSERT INTO [task].[Task] (sitegroup_id, name, description, task_class)
                VALUES (?, ?, ?, ?);
                SELECT SCOPE_IDENTITY() AS id;
            '''
            params = (self.sitegroup_id, self.name, self.description, self.task_class)
            result = execute_query(query, params, include_description=True)
            if result and isinstance(result, dict) and result['rows']:
                self.id = result['rows'][0]['id']
            flash(f'Task (ID: {self.id}) created successfully!')

    @classmethod
    def get_by_id(cls, task_id):
        query = 'SELECT * FROM [task].[Task] WHERE id = ?'
        result = execute_query(query, (task_id,), include_description=True)

        if result and result['rows']:
            row = result['rows'][0]
            task_class_name = row.get('task_class')
            task_class = cls.get_task_classes().get(task_class_name)
            if task_class:
                task = task_class()
                for k, v in row.items():
                    setattr(task, k, v)
                task.sitegroup = SiteGroup.get_by_id(task.sitegroup_id)
                return task
        return None

    @classmethod
    def get_all(cls):
        query = 'SELECT * FROM [task].[Task]'
        result = execute_query(query, include_description=True)
        tasks = []

        if result and result['rows']:
            for row in result['rows']:
                task_class_name = row.get('task_class')
                task_class = cls.get_task_classes().get(task_class_name)
                if task_class:
                    task = task_class()
                    for k, v in row.items():
                        setattr(task, k, v)
                    task.sitegroup = SiteGroup.get_by_id(task.sitegroup_id)
                    tasks.append(task)
        return tasks

    def delete(self):
        if hasattr(self, 'id'):
            query = 'DELETE FROM [task].[Task] WHERE id = ?'
            execute_query(query, (self.id,))
            del self.id
