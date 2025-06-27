import paramiko, io, csv
from settings import SITEGROUP_FTP_CREDENTIALS, FTP_SERVER
from misc import get_headers_sql

class SFTP(object):
	def __init__(self, sftp_key):
		if sftp_key not in SITEGROUP_FTP_CREDENTIALS:
			raise Exception(f"sftp_key '{sftp_key}' is not configured.")
		self.sftp_connection = None
		self.sftp_key = sftp_key
		self.server_name = SITEGROUP_FTP_CREDENTIALS.get(self.sftp_key, {}).get("host") or FTP_SERVER  # Use default server if not provided
		self.username = SITEGROUP_FTP_CREDENTIALS.get(self.sftp_key, {}).get("username")
		self.password = SITEGROUP_FTP_CREDENTIALS.get(self.sftp_key, {}).get("password")

		self.connect()

	def connect(self):
		try:
			ssh = paramiko.SSHClient()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			ssh.connect(self.server_name, username=self.username, password=self.password)
			self.sftp_connection = ssh.open_sftp()
			print(f"Connected to SFTP server '{self.server_name}' for client '{self.sftp_key}'.")
		except Exception as e:
			print(f"Failed to connect: {e}")

	def read_csv_data(self, file_name, encoding='utf-16', delimiter=','):
		"""Assumes the file is in the cwd of the ftp connection"""
		try:
			with self.sftp_connection.file(file_name, 'r') as file:
				csv_string = file.read().decode(encoding)
				return csv.reader(csv_string.splitlines(), delimiter=delimiter)
		except Exception as e:
			print(f"Failed to read file: {e}")
			return None

	def post_results_to_csv(self, result_set, file_name, include_headers=True, custom_headers=None):
		try:
			bytes_buffer = io.BytesIO()
			string_buffer = io.TextIOWrapper(bytes_buffer, encoding='utf-8')
			csv_writer = csv.writer(string_buffer, quoting=csv.QUOTE_ALL, lineterminator='\n')
	
			# write column headers
			csv_writer.writerow(get_headers_sql(result_set))
			# write data rows
			for row in result_set:
				csv_writer.writerow(row)
		
			string_buffer.flush()  # force String to send all from buffer to file (you can't use `iow.close()` for it)
			bytes_buffer.seek(0)  # Move the buffer cursor to the beginning before returning
	
			with self.sftp_connection.file(file_name, 'wb') as remote_file:
				for chunk in iter(lambda: bytes_buffer.read(4096), b''):
					remote_file.write(chunk)

			print(f"{file_name} posted successfully for sftp key '{self.sftp_key}'.")
		except Exception as e:
			print(f"Failed to post result_set to csv: {e}")
		finally:
            # Make sure to close the buffers or use context managers for proper resource cleanup
			string_buffer.close()
			bytes_buffer.close()
			
	def disconnect(self):
		if self.sftp_connection:
			self.sftp_connection.close()
			print("Disconnected from SFTP server.")			

if __name__ == '__main__':
	foo = 1