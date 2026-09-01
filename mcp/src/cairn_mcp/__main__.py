"""Entry point: `cairn-mcp` console script and `python -m cairn_mcp`."""

from .server import run_stdio


def main() -> None:
    run_stdio()


if __name__ == "__main__":
    main()
