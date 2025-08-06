"""Configuration management commands."""

from __future__ import annotations

import os

import click
import toml
from rich.console import Console
from rich.table import Table

from ...utils.paths import AUTH_DIR
from ..utils.formatting import format_error, format_success, format_warning

console = Console()


@click.group()
def config_group() -> None:
    """⚙️ Manage configuration and API keys."""
    pass


@config_group.command("show")
@click.option("--show-keys", is_flag=True, help="Show API keys (masked)")
def show_config(show_keys: bool) -> None:
    """Display current configuration."""
    try:
        config_file = AUTH_DIR / "config.toml"
        if not config_file.exists():
            console.print(
                format_warning(
                    "Configuration file not found",
                    f"Create {config_file} to store settings and API keys.",
                )
            )
            return

        config = toml.load(config_file)

        console.print("[bold blue]Current Configuration[/bold blue]\n")

        # General settings
        if "general" in config:
            console.print("[bold]General Settings:[/bold]")
            for key, value in config["general"].items():
                console.print(f"  {key}: {value}")
            console.print()

        # API settings
        if "api" in config:
            console.print("[bold]API Settings:[/bold]")
            for key, value in config["api"].items():
                if "key" in key.lower() and not show_keys:
                    # Mask API keys
                    masked = f"{str(value)[:8]}..." if value else "Not set"
                    console.print(f"  {key}: {masked}")
                else:
                    console.print(f"  {key}: {value}")
            console.print()

        # Other sections
        for section, settings in config.items():
            if section not in ["general", "api"]:
                console.print(f"[bold]{section.title()} Settings:[/bold]")
                for key, value in settings.items():
                    console.print(f"  {key}: {value}")
                console.print()

    except Exception as e:
        console.print(format_error(f"Failed to read configuration: {str(e)}"))


@config_group.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--section", default="general", help="Configuration section")
def set_config(key: str, value: str, section: str) -> None:
    """Set a configuration value.

    KEY: Configuration key to set
    VALUE: Value to set
    """
    try:
        config_file = AUTH_DIR / "config.toml"
        # Ensure config directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        if config_file.exists():
            config = toml.load(config_file)
        else:
            config = {}

        # Set value
        if section not in config:
            config[section] = {}

        # Try to parse value as appropriate type
        parsed_value = _parse_config_value(value)
        config[section][key] = parsed_value

        # Save config
        with open(config_file, "w") as f:
            toml.dump(config, f)

        console.print(format_success(f"Set {section}.{key} = {parsed_value}"))

    except Exception as e:
        console.print(format_error(f"Failed to set configuration: {str(e)}"))


@config_group.command("get")
@click.argument("key")
@click.option("--section", default="general", help="Configuration section")
def get_config(key: str, section: str) -> None:
    """Get a configuration value.

    KEY: Configuration key to get
    """
    try:
        config_file = AUTH_DIR / "config.toml"
        if not config_file.exists():
            console.print(format_error("Configuration file not found"))
            return

        config = toml.load(config_file)

        if section not in config:
            console.print(format_error(f"Section '{section}' not found"))
            return

        if key not in config[section]:
            console.print(format_error(f"Key '{key}' not found in section '{section}'"))
            return

        value = config[section][key]
        console.print(f"{section}.{key} = {value}")

    except Exception as e:
        console.print(format_error(f"Failed to get configuration: {str(e)}"))


@config_group.group("keys")
def keys_group() -> None:
    """Manage API keys."""
    pass


@keys_group.command("list")
def list_keys() -> None:
    """List all configured API keys."""
    try:
        config_file = AUTH_DIR / "config.toml"
        if not config_file.exists():
            console.print(format_warning("No configuration file found"))
            return

        config = toml.load(config_file)

        if "api" not in config:
            console.print("[dim]No API keys configured.[/dim]")
            return

        table = Table(title="API Keys", show_header=True, header_style="bold blue")
        table.add_column("Service")
        table.add_column("Status")
        table.add_column("Key Preview")

        for key, value in config["api"].items():
            if "key" in key.lower():
                service = key.replace("_key", "").replace("_", " ").title()
                status = "[green]✓ Set[/green]" if value else "[red]✗ Not set[/red]"
                preview = f"{str(value)[:8]}..." if value else "---"
                table.add_row(service, status, preview)

        console.print(table)

    except Exception as e:
        console.print(format_error(f"Failed to list API keys: {str(e)}"))


@keys_group.command("set")
@click.argument("service", type=click.Choice(["openai", "oxford"]))
@click.argument("api_key")
def set_key(service: str, api_key: str) -> None:
    """Set an API key for a service.

    SERVICE: The service name (openai, oxford)
    API_KEY: The API key to set
    """
    try:
        config_file = AUTH_DIR / "config.toml"
        # Ensure config directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        if config_file.exists():
            config = toml.load(config_file)
        else:
            config = {}

        # Set API key
        if "api" not in config:
            config["api"] = {}

        key_name = f"{service}_key"
        config["api"][key_name] = api_key

        # Save config
        with open(config_file, "w") as f:
            toml.dump(config, f)

        console.print(format_success(f"Set API key for {service}"))

    except Exception as e:
        console.print(format_error(f"Failed to set API key: {str(e)}"))


@keys_group.command("test")
@click.option(
    "--service",
    type=click.Choice(["all", "openai", "oxford"]),
    default="all",
    help="Service to test",
)
def test_keys(service: str) -> None:
    """Test API key connectivity.

    Makes simple API calls to verify that keys are working.
    """
    console.print(f"[bold blue]Testing API connectivity for: {service}[/bold blue]")

    if service == "all":
        services = ["openai", "oxford"]
    else:
        services = [service]

    for svc in services:
        console.print(f"\n[bold]{svc.title()}:[/bold]")
        console.print("[dim]API testing not yet implemented.[/dim]")


@config_group.command("edit")
def edit_config() -> None:
    """Open configuration file in default editor."""
    try:
        config_file = AUTH_DIR / "config.toml"
        if not config_file.exists():
            # Create default config file
            config_file.parent.mkdir(parents=True, exist_ok=True)
            default_config = {
                "general": {
                    "output_format": "rich",
                    "default_provider": "ai_synthesis",
                    "max_results": 10,
                },
                "api": {
                    "openai_key": "",
                    "oxford_key": "",
                    "rate_limit_enabled": True,
                },
                "anki": {
                    "default_card_types": ["best_describes", "fill_in_blank"],
                    "max_cards_per_word": 2,
                    "export_format": "apkg",
                },
                "search": {
                    "fuzzy_threshold": 0.6,
                    "vector_similarity_threshold": 0.7,
                    "max_fuzzy_results": 20,
                },
            }

            with open(config_file, "w") as f:
                toml.dump(default_config, f)

            console.print(format_success(f"Created default configuration file: {config_file}"))

        # Open in editor
        editor = os.environ.get("EDITOR", "nano")
        os.system(f"{editor} {config_file}")

    except Exception as e:
        console.print(format_error(f"Failed to edit configuration: {str(e)}"))


@config_group.command("reset")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def reset_config(confirm: bool) -> None:
    """Reset configuration to defaults."""
    if not confirm:
        if not click.confirm("Reset all configuration to defaults?"):
            console.print("Operation cancelled.")
            return

    try:
        config_file = AUTH_DIR / "config.toml"
        if config_file.exists():
            config_file.unlink()

        console.print(format_success("Configuration reset to defaults"))
        console.print("[dim]Run 'floridify config edit' to customize settings.[/dim]")

    except Exception as e:
        console.print(format_error(f"Failed to reset configuration: {str(e)}"))


def _parse_config_value(value: str) -> str | int | float | bool:
    """Parse a string value to appropriate type."""
    # Try boolean
    if value.lower() in ["true", "yes", "on"]:
        return True
    elif value.lower() in ["false", "no", "off"]:
        return False

    # Try integer
    try:
        return int(value)
    except ValueError:
        pass

    # Try float
    try:
        return float(value)
    except ValueError:
        pass

    # Return as string
    return value
