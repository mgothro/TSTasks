import smtplib, settings as s
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class Emailer(object):
	"""description of class"""
	def __init__(self):
		self.from_address = s.DEFAULT_FROM_EMAIL
		self.to_address = ''
		self.cc_address = ''
		self.subject = ''
		self.body = ''

	def send(self):
		msg = MIMEMultipart()
		msg.attach(MIMEText(self.body, 'html'))
		msg['From'] = self.from_address
		msg['To'] = self.to_address
		msg['Cc'] = self.cc_address
		msg['Subject'] = self.subject

		smtp_server_name = s.EMAIL_SERVER
		port = '25' # for normal messages

		server = smtplib.SMTP('{}:{}'.format(smtp_server_name, port))

		server.send_message(msg)
		server.quit()

	@property
	def to_address(self):
		return self._to_address

	@to_address.setter
	def to_address(self, value):
		self._to_address = value

	@property
	def from_address(self):
		return self._from_address

	@from_address.setter
	def from_address(self, value):
		self._from_address = value

	@property
	def subject(self):
		return self._subject

	@subject.setter
	def subject(self, value):
		self._subject = value

	@property
	def body(self):
		return self._body

	@body.setter
	def body(self, value):
		self._body = value

	@property
	def cc_address(self):
		return self._cc_address

	@cc_address.setter
	def cc_address(self, value):
		self._cc_address = value
