import typer


def install_playwright_browsers() -> None:
    """Run ``playwright install`` when crawl4ai is available.

    crawl4ai depends on Playwright and requires browsers to be downloaded
    separately. This is a no-op when langclaw[search] is not installed.
    """
    import importlib.util
    import subprocess
    import sys

    if importlib.util.find_spec("crawl4ai") is None:
        return

    typer.echo("\nInstalling Playwright browsers (required by crawl4ai)...")
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install"],
        capture_output=False,
    )
    if result.returncode == 0:
        typer.echo("Playwright browsers installed.")
    else:
        typer.echo(
            "Playwright browser install failed. Run manually: playwright install",
            err=True,
        )


def install_deps() -> None:
    """Automatically install all dependencies"""
    # Install Playwright browsers
    install_playwright_browsers()
