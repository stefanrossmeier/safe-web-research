__version__ = "0.1.0"


def main() -> int:
    from safe_web_research.cli import main as cli_main

    return cli_main()
