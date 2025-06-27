from models.task import Task
from dbconn import execute_query


class TestClass(Task):
	def __init__(self):		
		super().__init__()
		
	def run(self):
		sql = 'exec task.[tasktest]'
		results = execute_query

		
if __name__ == '__main__':
	TestClass().run()
