from datetime import timedelta
from time import time

SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = 3600
MAX_PERCENTAGE = 100
NUM_PROGRESS_BAR_DIVISIONS = 20
SECONDS_PER_UPDATE = 0.25

last_update = 0


# Takes in a progress percentage between 0 and 100, inclusive,
# and runtime info to display a progress bar.
def use_progress_bar(progress: int, start: float, end: float) -> None:
    if progress < 0 or progress > MAX_PERCENTAGE:
        raise Exception("Progress percentage must be between 0 and 100.")

    loaded = "\u25A0" * (progress // (MAX_PERCENTAGE // NUM_PROGRESS_BAR_DIVISIONS))
    not_loaded = "-" * (NUM_PROGRESS_BAR_DIVISIONS - len(loaded))
    progress_str = f"|{loaded}{not_loaded}|"
    pct_spaces = " " * (len(str(MAX_PERCENTAGE)) - len(str(progress)))
    pct_str = f"{pct_spaces}{progress}%"

    elapsed = timedelta(seconds=end - start)
    elapsed_str = str(elapsed).split(".")[0]
    time_str = f"[elapsed: {str(elapsed_str)}"

    if progress > 1:
        remaining = timedelta(
            seconds=int((end - start) * (MAX_PERCENTAGE / progress - 1))
        )
        remaining_str = str(remaining).split(".")[0]
        # remaining = int((end - start) * (MAX_PERCENTAGE / progress - 1))
        time_str += f", remaining: {remaining_str}]"
    else:
        time_str += "]"

    print(f"Progress: {progress_str} {pct_str} {time_str}", end="\r")


def should_update_progress_bar() -> bool:
    global last_update
    curr_time = time()
    if curr_time - last_update > SECONDS_PER_UPDATE:
        last_update = curr_time
        return True
    return False
