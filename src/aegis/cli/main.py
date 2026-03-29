import click

@click.group()
@click.version_option(package_name="aegis-dev")
def cli():
    """Aegis — Development Process Compiler.

    Enforces structured, verifiable AI-assisted development through
    a Plan -> Build -> Review pipeline with schema-validated interface
    documents.
    """

@cli.command()
def init():
    """Initialize an Aegis project in the current directory."""
    click.echo("aegis init: not yet implemented")

@cli.command()
def plan():
    """Run the planning stage."""
    click.echo("aegis plan: not yet implemented")

@cli.command()
def build():
    """Run the build stage on the latest PlanDocument."""
    click.echo("aegis build: not yet implemented")

@cli.command()
def status():
    """Show pipeline status and recent documents."""
    click.echo("aegis status: not yet implemented")
