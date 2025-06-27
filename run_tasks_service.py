import requests, time, logging

logging.basicConfig(
    filename=r"C:\inetpub\logs\run_tasks_service.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

while True:
    try:
        resp = requests.get("https://tstasks.cityspan.com/run_tasks", timeout=10)
        # Log status code
        logging.info(f"Ping returned HTTP {resp.status_code}")
        # Log raw body
        logging.info(f"Response body: {resp.text}")
        try:
            data = resp.json()
            logging.info(f"Parsed JSON: {data}")
        except ValueError:
            logging.warning("Response was not valid JSON")
    except Exception:
        logging.exception("Ping failed")
    time.sleep(60)
	