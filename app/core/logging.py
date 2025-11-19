import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(log_dir: str = "logs") -> None:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    server_log = log_path / "server.log"
    activity_log = log_path / "activity.log"

    logging.basicConfig(level=logging.INFO)

    server_handler = RotatingFileHandler(server_log, maxBytes=5 * 1024 * 1024, backupCount=5)
    server_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - PID:%(process)d - %(message)s")
    )

    activity_handler = RotatingFileHandler(activity_log, maxBytes=5 * 1024 * 1024, backupCount=5)
    activity_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(message)s")
    )

    server_logger = logging.getLogger("server")
    if not server_logger.handlers:
        server_logger.addHandler(server_handler)
        server_logger.setLevel(logging.INFO)

    activity_logger = logging.getLogger("user_activity")
    if not activity_logger.handlers:
        activity_logger.addHandler(activity_handler)
        activity_logger.setLevel(logging.INFO)
