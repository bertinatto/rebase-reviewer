# For colored terminal output
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print header text in purple."""
    print(f"{bcolors.HEADER}{text}{bcolors.ENDC}")


def print_success(text):
    """Print success text in green."""
    print(f"{bcolors.OKGREEN}{text}{bcolors.ENDC}")


def print_info(text):
    """Print info text in blue."""
    print(f"{bcolors.OKBLUE}{text}{bcolors.ENDC}")


def print_cyan(text):
    """Print cyan text."""
    print(f"{bcolors.OKCYAN}{text}{bcolors.ENDC}")


def print_warning(text):
    """Print warning text in yellow."""
    print(f"{bcolors.WARNING}{text}{bcolors.ENDC}")


def print_fail(text):
    """Print failure text in red."""
    print(f"{bcolors.FAIL}{text}{bcolors.ENDC}")


def print_bold(text):
    """Print bold text."""
    print(f"{bcolors.BOLD}{text}{bcolors.ENDC}")


def colorize(text, color=""):
    """Return text with color codes."""
    color_map = {
        "header": bcolors.HEADER,
        "blue": bcolors.OKBLUE,
        "cyan": bcolors.OKCYAN,
        "green": bcolors.OKGREEN,
        "warning": bcolors.WARNING,
        "fail": bcolors.FAIL,
        "bold": bcolors.BOLD,
    }
    color_code = color_map.get(color.lower(), "")
    return f"{color_code}{text}{bcolors.ENDC}" if color_code else text