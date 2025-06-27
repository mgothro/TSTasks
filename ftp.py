from ftplib import FTP_TLS, FTP as f
import settings as s
import io, csv, openpyxl, xlsxwriter
from misc import get_headers_sql
import chardet

class FTP(object):
	def __init__(self, sitegroup, protocol='SFTP'):
		if sitegroup not in s.SITEGROUP_FTP_CREDENTIALS:
			raise Exception(f"Sitegroup '{sitegroup}' is not configured for FTP.")

		self.sitegroup = sitegroup
		self.server_name = s.SITEGROUP_FTP_CREDENTIALS.get(self.sitegroup, {}).get("host") or s.FTP_SERVER  # Use default server if not provided
		self.username = s.SITEGROUP_FTP_CREDENTIALS.get(self.sitegroup, {}).get("username")
		self.password = s.SITEGROUP_FTP_CREDENTIALS.get(self.sitegroup, {}).get("password")
		self.ftp_connection = None
		
		if protocol == 'SFTP':
			self.connect_sftp()
		elif protocol == 'FTP':
			self.connect_ftp()
		else:
			raise Exception(f"Protocol '{protocol}' is not supported.")

	def connect_sftp(self):
		try:
			self.ftp_connection = FTP_TLS(self.server_name)
			self.ftp_connection.connect(self.server_name)
			self.ftp_connection.login(user=self.username, passwd=self.password)
			self.ftp_connection.prot_p()  # Set up secure data connection
			print(f"Connected to SFTP server '{self.server_name}' for client '{self.sitegroup}'.")
		except Exception as e:
			print(f"Failed to connect: {e}")

	def connect_ftp(self):
		try:
			self.ftp_connection = f()
			self.ftp_connection.connect(self.server_name)
			self.ftp_connection.login(user=self.username, passwd=self.password)
			print(f"Connected to FTP server '{self.server_name}' for client '{self.sitegroup}'.")
		except Exception as e:
			print(f"Failed to connect: {e}")

	#pass in None, leave defaults as they were
	def read_csv_data(self, file_name, encoding='utf-16', delimiter=','):
		"""Assumes the file is in the cwd of the ftp connection"""
		bytes_buffer = io.BytesIO()
		self.ftp_connection.retrbinary('RETR %s' % file_name, bytes_buffer.write)
		bytes_data = bytes_buffer.getvalue()

		if encoding is None:
			detected_encoding = chardet.detect(bytes_data)['encoding']
			encoding = detected_encoding if detected_encoding else 'utf-16'
			
		csv_string = bytes_data.decode(encoding)
		
		if delimiter is None:
			try:
				sniffer = csv.Sniffer()
				sample = csv_string[:1024]
				dialect = sniffer.sniff(sample)
				delimiter = dialect.delimiter
			except Exception as e:
				print(f"Failed to detect delimiter: {e}")
				delimiter = ','
			
		return csv.reader(csv_string.splitlines(), delimiter=delimiter)

	def read_xlsx_data(self, file_name, sheet_name=None):
		"""
		Reads data from an XLSX file on the FTP server using openpyxl.
		Assumes the file is in the cwd of the ftp connection.
		Returns a list of lists, where each inner list represents a row in the spreadsheet.
		Filters out columns with no header values.
	
		Args:
			file_name (str): The name of the XLSX file on the FTP server.
			sheet_name (str, optional): The name of the worksheet to read. If None, the active sheet is used. Defaults to None.
		"""
		bytes_buffer = io.BytesIO()
		self.ftp_connection.retrbinary('RETR %s' % file_name, bytes_buffer.write)
		bytes_data = bytes_buffer.getvalue()
		try:
			# Load the workbook from the in-memory byte stream
			workbook = openpyxl.load_workbook(io.BytesIO(bytes_data))
			# Get the worksheet
			if sheet_name:
				sheet = workbook[sheet_name]  # Access sheet by name
			else:
				sheet = workbook.active  # Use the active sheet
			
			# Get all rows as a list of lists
			all_rows = []
			for row in sheet.iter_rows(values_only=True):
				all_rows.append(list(row))
			
			# Check if we have any data
			if not all_rows:
				return []
			
			# Get the headers (first row)
			headers = all_rows[0]
		
			# Find valid column indices (columns with non-empty headers)
			valid_indices = []
			for i, header in enumerate(headers):
				# Consider a header valid if it's not None and, if it's a string, not empty after stripping
				if header is not None and (not isinstance(header, str) or header.strip()):
					valid_indices.append(i)
				
			# Filter the data to include only columns with valid headers
			filtered_data = []
			for row in all_rows:
				# Make sure we don't try to access indices that don't exist in the row
				filtered_row = [row[i] for i in valid_indices if i < len(row)]
				filtered_data.append(filtered_row)
			
			return filtered_data
		
		except KeyError:
			print(f"Sheet '{sheet_name}' not found in workbook.")
			return None
		except Exception as e:
			print(f"Error reading XLSX file: {e}")
			return None

	def post_results_to_csv(self, result_set, file_name, include_headers=True, custom_headers=None):
		try:
			bytes_buffer = io.BytesIO()
			string_buffer = io.TextIOWrapper(bytes_buffer, encoding='utf-8')

			csv_writer = csv.writer(string_buffer, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')

			# Write headers only if include_headers is True and custom_headers is not provided
			if include_headers:
				if custom_headers:
					for header_row in custom_headers:
						csv_writer.writerow(header_row)
				else:
					csv_writer.writerow(get_headers_sql(result_set))
	
			for row in result_set:
				csv_row = []
				for field in row:
					csv_row.append(field)
				
				csv_writer.writerow(csv_row)
		
			string_buffer.flush()  # force String to send all from buffer to file (you can't use `iow.close()` for it)
			bytes_buffer.seek(0)  # Move the buffer cursor to the beginning before returning
	
			self.ftp_connection.storbinary(f"STOR {file_name}", bytes_buffer)
			print(f"{file_name} posted successfully for client '{self.sitegroup}'.")
		except Exception as e:
			print(f"Failed to post results to csv: {e}")
		finally:
			# Make sure to close the buffers or use context managers for proper resource cleanup
			string_buffer.close()
			bytes_buffer.close()

	def post_row_dicts_to_csv(self, result_set, file_name, include_headers=True, custom_headers=None, write_empty_file = False):
		"""Posts a list of dictionaries (CaseInsensitiveDict) to a CSV file via FTP.

		Args:
			result_set: A list of dictionaries (CaseInsensitiveDict objects).
			file_name: The name of the CSV file to create on the FTP server.
			include_headers: Whether to include headers in the CSV.
			custom_headers: Optional custom headers (list of lists). If provided, overrides automatic header generation.
				for custom header, execute_query has option to return cursor.description .. pass that in as the custom_headers`
		"""
		try:
			with io.BytesIO() as bytes_buffer, io.TextIOWrapper(bytes_buffer, encoding='utf-8') as string_buffer:
				csv_writer = csv.writer(string_buffer, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')

				# Determine fieldnames based on the dictionaries.  Use the first one if possible.
				if result_set:  # Check if result_set is not empty
					fieldnames = list(result_set[0].keys())  # Get keys from the first dict

					# Write headers only if include_headers is True
					if include_headers:
						if custom_headers:
							for header_row in custom_headers:
								csv_writer.writerow(header_row)
						else:
							csv_writer.writerow(fieldnames)  # Use fieldnames as headers
				elif write_empty_file:
					for header_row in custom_headers:
						csv_writer.writerow(header_row)
				else:
					print("Warning: result_set is empty.  No CSV will be written.")
					return  # Exit if result_set is empty.

				for row_dict in result_set:
					csv_row = []
					for fieldname in fieldnames: #iterate through the fieldnames to make sure the order matches and is consistent.
						csv_row.append(row_dict.get(fieldname, ''))  # Use get() to handle missing fields

					csv_writer.writerow(csv_row)

				string_buffer.flush()  # Force String to send all from buffer to file
				bytes_buffer.seek(0)  # Move the buffer cursor to the beginning

				self.ftp_connection.storbinary(f"STOR {file_name}", bytes_buffer)
				print(f"{file_name} posted successfully for client '{self.sitegroup}'.")

		except Exception as e:
			print(f"Failed to post results to csv: {e}")


	def post_excel_from_recordsets(self, recordsets, file_name, worksheet_names=None):
		"""Posts multiple recordsets to an Excel file with each recordset as a separate worksheet.

		Args:
			recordsets: A list of recordsets (lists of tuples).
			file_name: The name of the Excel file to create on the FTP server.
			worksheet_names: A dictionary mapping recordset index to worksheet name.
							   If None, default names ('Sheet1', 'Sheet2', etc.) are used.
		"""

		try:
			# Create an in-memory byte stream to hold the Excel file
			excel_buffer = io.BytesIO()

			# Create an XlsxWriter workbook using the in-memory stream
			workbook = xlsxwriter.Workbook(excel_buffer)

			if worksheet_names is None:
				worksheet_names = {}  # Use an empty dict if None is passed.

			# Process each recordset
			for i, recordset in enumerate(recordsets):
				# Determine the worksheet name
				if i in worksheet_names:
					worksheet_name = worksheet_names[i][:31]  # Limit to 31 characters
				else:
					worksheet_name = f'Sheet{i+1}'  # Default name

				# Create a new worksheet
				worksheet = workbook.add_worksheet(worksheet_name)
				self._write_recordset_to_worksheet(worksheet, recordset)


			# Close the workbook to finalize the Excel file
			workbook.close()

			# Prepare to upload the Excel file
			excel_buffer.seek(0)  # Rewind the buffer to the beginning

			# Upload the Excel file to the FTP server
			self.ftp_connection.storbinary(f"STOR {file_name}", excel_buffer)
			print(f"{file_name} posted successfully for client '{self.sitegroup}'.")

		except Exception as e:
			print(f"Failed to post results to Excel: {e}")
		finally:
			excel_buffer.close()


	def _write_recordset_to_worksheet(self, worksheet, recordset):
		"""Writes a recordset to an XlsxWriter worksheet.

		Args:
			worksheet: The XlsxWriter worksheet object.
			recordset: A list of tuples representing the data.
		"""
		if not recordset:
			return #nothing to write

		# Write the headers
		headers = [str(h) for h in recordset[0].keys()] #convert to string just in case
		for col_num, header in enumerate(headers):
			worksheet.write(0, col_num, header)

		# Write the data rows
		for row_num, row_data in enumerate(recordset):
			for col_num, cell_data in enumerate(row_data.values()):
				try:
					worksheet.write(row_num + 1, col_num, cell_data)
				except TypeError:
					worksheet.write(row_num + 1, col_num, str(cell_data)) #try converting to a string
					
	def disconnect(self):
		if self.ftp_connection:
			self.ftp_connection.quit()
			print("Disconnected from FTP server.")			
			

	def post_dedupe_generate_file(self, results, file_name):
		output = io.BytesIO()
		workbook = xlsxwriter.Workbook(output, {'in_memory': True})
		worksheet = workbook.add_worksheet()
			
		shade_style = workbook.add_format()
		shade_style.set_bg_color('#c0c0c0')
		bold_font = workbook.add_format({'bold': True})
			
		headers = [str(h) for h in results[0].keys()] #convert to string just in case
		for ix, header in enumerate(headers):
			worksheet.write(0, ix, header)

		#write data rows
		for row_ix, row in enumerate(results):
			row_ix += 1
			style = None
			if row['Grouping ID'] % 2 == 1:
				style = shade_style

			for col_ix, col in enumerate(headers):
				worksheet.write(row_ix, col_ix, row[col], style)
					
		workbook.close()
		# Rewind the buffer
		output.seek(0)
			
		self.ftp_connection.storbinary('STOR ' + file_name, output)
	

if __name__ == '__main__':
	foo = 1
	