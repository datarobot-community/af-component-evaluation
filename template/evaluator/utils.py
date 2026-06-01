from datetime import datetime


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
