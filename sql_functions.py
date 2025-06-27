from dbconn import execute_query, execute_many

def drop_table(table_name, database='fastworkspace', schema='task'):
    #Parameters:
    #   table_name - str

    full_table_name = f'{database}.{schema}.{table_name}'
    sql = f"if object_id('{full_table_name}') is not null drop table {full_table_name}"
    execute_query(sql)

def create_table(table_name, headers=[], database='fastworkspace', schema='task'):
    #Parameters:
    #   table_name - str
    #   headers[] - list of str

    full_table_name = f'{database}.{schema}.{table_name}'
    columns = ', '.join([f'[{header}] varchar(5000)' for header in headers])
    sql = f"create table {full_table_name} ({columns})"
    execute_query(sql)

def insert_data(table_name, headers, data, database='fastworkspace', schema='task'):
    #Parameters:
    #   table_name - str
    #   headers[] - list of str
    #   data[] - list of lists of str

    full_table_name = f'{database}.{schema}.{table_name}'
    placeholders = ', '.join(['?'] * len(headers))
    sql = f"insert into {full_table_name} values ({placeholders})"
    execute_many(sql, data)


def import_stats_email(import_logid):
    results = execute_query(f"""
        select l.Id, JobId, SubjobId, ProcessTime, Outcome, FailReason, Filename, NumRowsInFile, j.Name, IsNull(dr.discardedrows,0) as discardedrows, IsNull(z.newPersonCt, 0) as newPersonCt
        from import.Log l with (nolock)
        inner join import.jobs j with (nolock)
            on j.id = l.jobid 
        left join (
            select importlogid, count(distinct rowid) as discardedrows
            from import.discardedrows with (nolock)
            where importlogid = {import_logid}
            group by importlogid
        ) dr 
            on dr.importlogid = l.id
        left join (
	        select l.Id, count(*) as newPersonCt
	        from PersonCore pc with (nolock)
	        inner join import.Jobs j with (nolock)
		        on j.SiteGroupId = pc.SiteGroupId
	        inner join import.Log l with (nolock)
		        on l.JobId = j.Id
		        and l.Id = {import_logid}
		        and l.ProcessTime = pc.CreationDate
	        group by l.Id
        ) z
	        on z.Id = l.Id
        where l.Id = {import_logid}
    """)

    if not results:
        return None  # Or raise an exception if results are always expected

    result = results[0]
    job_id = result.get('JobId', 'N/A')  # Use get() with default values
    job_name = result.get('Name', 'N/A')
    process_time = result.get('ProcessTime', 'N/A')
    outcome = result.get('Outcome', 'N/A')
    fail_reason = result.get('FailReason', '')
    filename = result.get('Filename', 'N/A')
    num_rows_in_file = result.get('NumRowsInFile', 'N/A')
    discarded_rows = result.get('discardedrows', 0)
    new_persons = result.get('newPersonCt', 'N/A')
    import_logid = result.get('importLogId', None)

    # Conditionally fetch discarded rows message. We need the import_logid
    discarded_rows_message = ''
    if discarded_rows > 0:
        discarded_rows_message = f"""<p><span class="field-label">A file containing the discarded rows can be found in the SFTP folder where the original file was located.</p>"""
        
    # Format the fail reason nicely
    formatted_fail_reason = f"\n\n<b>Fail Reason:</b> {fail_reason}" if fail_reason else ""

    # Use HTML for better formatting in email clients
    email_body = f"""
<html>
<head>
    <style>
        body {{font-family: Arial, sans-serif;}}
        .section-title {{font-size: 1.2em; font-weight: bold; margin-top: 10px;}}
        .field-label {{font-weight: bold;}}
    </style>
</head>
<body>
    <p class="section-title">Import Job Results:</p>
    <p><span class="field-label">Job ID:</span> {job_id}</p>
    <p><span class="field-label">Job Name:</span> {job_name}</p>
    <p><span class="field-label">Process Time:</span> {process_time}</p>
    <p><span class="field-label">Outcome:</span> {outcome}{formatted_fail_reason}</p>
    <p><span class="field-label">Filename:</span> {filename}</p>
    <p><span class="field-label">Number of New Persons:</span> {new_persons}</p>
    <p><span class="field-label">Number of Rows in File:</span> {num_rows_in_file}</p>
    <p><span class="field-label">Number of Discarded Rows:</span> {discarded_rows}</p>
    {discarded_rows_message}
</body>
</html>
"""

    return email_body

def import_get_discarded_rows(import_logid):
    return execute_query(f"""exec sms.import.getDiscardedRows @importLogId = {import_logid}""")
