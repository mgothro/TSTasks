# TSTasks

TSTasks is a lightweight task scheduling and execution system built with Flask and Python. 
It enables scheduling and automated execution of database, email, and file-transfer tasks across multiple client environments, with support for tracking, reporting, and logging.

---

## Features

- Task creation and management via web interface
- Schedule tasks by frequency and interval (daily, monthly, etc.)
- Execute tasks manually or via automated runner (windows service)
- Track task execution history and errors
- Send email notifications using Postmark or SMTP
- Upload/download files via FTP/SFTP
- Modular architecture for defining and adding custom task classes

---

## Project Structure

```
TSTasks/
├── models/             # ORM-style models for Tasks, Schedules, Results
├── tasks/              # Custom task class implementations
├── static/             # CSS and JS files
├── templates/          # HTML templates for Flask routes
├── dbconn.py           # DB connection and query execution utilities
├── config.py           # Application configuration
├── emailer.py          # Email sending functionality
├── ftp.py / sftp.py    # File transfer utilities
├── server.py           # Flask app initialization
├── schedule_executor.py# Scheduled task runner
├── run_tasks_service.py# Entry point for CLI/task service. Used to create .exe via Pyinstaller and set up as a windows service
```

---

## Getting Started

### Requirements

- Python 3.8+
- Microsoft SQL Server (or compatible DB)
- Access credentials for Postmark (if using email notifications)

### Installation

1. Clone the repo:

```bash
git clone https://github.com/mgothro/TSTasks.git
cd TSTasks
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up environment variables (or edit `config.py`):

```bash
export DB_SERVER=your_sql_server
export POSTMARK_API_KEY=your_postmark_key
```

5. Run the Flask server:

```bash
python server.py
```

---

## Usage

- Visit `http://localhost:5000` to access the web interface.
- Define new tasks and schedules.
- Use `run_tasks_service.py` or `schedule_executor.py` to trigger scheduled jobs.

---

## Custom Tasks

You can define your own task types by:

1. Creating a new class in the `tasks/` directory.
2. Inheriting from the abstract `Task` class.
3. Implementing the `run()` method with your custom logic.
4. Registering the task class in your task creation process.

---

## To Do

- Build an API layer for remote task scheduling
- Improve UI feedback and error visibility
- Add unit tests and CI support

---

## Author

Matthew Gothro
[github.com/mgothro](https://github.com/mgothro)
