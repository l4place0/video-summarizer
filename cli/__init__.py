"""video-sum CLI — lightweight orchestration layer for video summarization."""

import click


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Video Summarizer CLI — structured JSON output for skill integration."""
    pass


from cli.commands import run, submit, status, result  # noqa: E402

main.add_command(run)
main.add_command(submit)
main.add_command(status)
main.add_command(result)
