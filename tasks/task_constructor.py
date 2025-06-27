from models.task import Task

class TaskConstructor(Task):
	def __init__(self, sitegroup_id, name, description, task_class):		
		self.sitegroup_id = sitegroup_id
		self.name = name
		self.description = description
		self.task_class = task_class
		
		super().__init__()
		
	def run(self):
		"""
		YOUR CODE HERE
		"""