from datetime import datetime
from emailer import Emailer
import traceback
from models.task import Task
from models.emailrecipient import EmailRecipient
from models.executionresult import ExecutionResult

class ScheduleExecutor(object):
	
	ERROR_STRING = 'Error'
	SUCCESS_STRING = 'Success'
	RUNNING_STRING = 'Running'

	def __init__(self, schedule):
		self.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
		self.email_recipients = EmailRecipient().get_recipients_for_schedule(schedule.id)
		self.task = Task.get_by_id(schedule.task_id)
		self.schedule = schedule
		
		self.emailer = Emailer()
		self.error_messages = []

	def execute(self):
		try:
			self.task.run()
		except Exception:
			self.error_messages.append(f'Task execution failed: {traceback.format_exc()}')
		finally:
			self.error_messages.extend(self.task.error_messages)
			self.log_results()
			self.email_results()
		return

	def email_results(self):
		status = ScheduleExecutor.SUCCESS_STRING if len(self.error_messages) == 0 else ScheduleExecutor.ERROR_STRING
		
		if status == ScheduleExecutor.ERROR_STRING:
			#force email to send if there was an error
			self.task.send_email = True

		if self.task.send_email:
			#Defaults
			self.emailer.to_address = ';'.join([x.email for x in self.email_recipients])
			self.emailer.subject = self.schedule.email_subject + f' (Run Status: {status})'
			
			#Overrides from task
			if hasattr(self.task, 'email_subject'):
				self.emailer.subject = self.task.email_subject

			if status == ScheduleExecutor.SUCCESS_STRING:
				self.emailer.body = self.task.email_body
			else:
				self.emailer.body = f'Details can be found in the Task.ExecutionResult database table (id:{self.execution_result.id}).'
				
			self.emailer.send()
			
		return

	def log_results(self):
		status = ScheduleExecutor.SUCCESS_STRING if len(self.error_messages) == 0 else ScheduleExecutor.ERROR_STRING
		
		self.execution_result = ExecutionResult(
				task_id=self.task.id,
				schedule_id=self.schedule.id,
				start_time=self.start_time,
				end_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
				status=status,
				error_message='\r\n'.join(self.error_messages).replace("'", "''")
				)
		
		self.execution_result.save()
		
		return
	
	@property
	def task(self):
		return self._task
	
	@task.setter
	def task(self, task):
		self._task = task
		
	@property
	def schedule(self):
		return self._schedule

	@schedule.setter
	def schedule(self, schedule):
		self._schedule = schedule
	
	@property
	def email_recipients(self):
		return self._email_recipients

	@email_recipients.setter
	def email_recipients(self, email_recipients):
		self._email_recipients = email_recipients		

	@property
	def status(self):
		return self._status

	@status.setter
	def status(self, status):
		self._status = status