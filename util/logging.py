import logging
import os
import sys
from datetime import datetime

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_global_logging(logging_level: int):
    log_file_name = (
        f"log/consensus-log-{datetime.now().isoformat(timespec='minutes')}.log"
    )
    os.makedirs("log", exist_ok=True)

    logging.basicConfig(
        level=logging_level,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file_name, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logging.getLogger("spade").setLevel(logging.INFO)
    logging.getLogger("spade.Agent").setLevel(logging.ERROR)
    logging.getLogger("slixmpp").setLevel(logging.ERROR)
