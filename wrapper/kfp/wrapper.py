import os

import digitalhub as dh
from digitalhub.utils.logger import LOGGER


def main():
    """
    Main function. Get run from backend and execute function.
    """

    LOGGER.info("Getting run from backend.")
    run = dh.get_run(os.getenv("RUN_ID"), os.getenv("PROJECT_NAME"))

    LOGGER.info("Executing function.")
    run.run()

    LOGGER.info("Done.")


if __name__ == "__main__":
    main()
