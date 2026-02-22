"""CLI entry point using Typer."""

import typer

app = typer.Typer(
    name="colab-push",
    help="Push code to Google Colab from the command line.",
    add_completion=False,
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Push code to Google Colab from the command line."""
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())


def app_entry():
    app()
