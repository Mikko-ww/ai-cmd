import sys
import os

class LogColor:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

def supports_color():
    return (
        hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
        and os.environ.get("TERM", "").lower() != "dumb"
    )

class Logger:
    def __init__(self, use_color: bool = True):
        self.use_color = use_color and supports_color()

    def _colorize(self, text: str, color: str) -> str:
        if not self.use_color:
            return text
        color_code = getattr(LogColor, color.upper(), "")
        return f"{color_code}{text}{LogColor.RESET}"

    def info(self, msg: str):
        print(self._colorize(msg, "blue"))

    def success(self, msg: str):
        print(self._colorize(msg, "green"))

    def warning(self, msg: str):
        print(self._colorize(msg, "yellow"))

    def error(self, msg: str):
        print(self._colorize(msg, "red"), file=sys.stderr)

    def bold(self, msg: str):
        print(self._colorize(msg, "bold"))

    def print(self, msg: str):
        print(msg)

# Example usage:
# logger = Logger()
# logger.info("This is info")
# logger.success("Success message")
# logger.warning("Warning message")
# logger.error("Error message")
# logger.bold("Bold message")
# logger.plain("Plain message")

logger = Logger()