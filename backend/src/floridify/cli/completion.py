"""ZSH completion generation for floridify CLI."""

import click


def generate_zsh_completion() -> str:
    """Generate ZSH completion script for floridify."""
    completion_script = """#compdef floridify

_floridify() {
    local context state line
    typeset -A opt_args

    _arguments -C \\
        '1: :->command' \\
        '*: :->args' && return 0

    case $state in
        command)
            _values "floridify command" \\
                "lookup[Look up word definitions with AI enhancement]" \\
                "define[Alias for lookup]" \\
                "search[Search functionality - find words across lexicons]" \\
                "scrape[Scraping commands for systematic provider data collection]" \\
                "wordlist[Manage word lists with dictionary lookup and storage]" \\
                "config[Manage configuration and API keys]" \\
                "database[Database operations and statistics]" \\
                "wotd-ml[WOTD ML with multi-model support]" \\
                "--help[Show help message]" \\
                "--version[Show version information]"
            ;;
        args)
            case $line[1] in
                scrape)
                    _floridify_scrape
                    ;;
                lookup|define)
                    _floridify_lookup
                    ;;
                search)
                    _floridify_search
                    ;;
                config)
                    _floridify_config
                    ;;
                database)
                    _floridify_database
                    ;;
                wordlist)
                    _files
                    ;;
            esac
            ;;
    esac
}

_floridify_scrape() {
    _arguments -C \\
        '1: :->scrape_command' \\
        '*: :->scrape_args' && return 0

    case $state in
        scrape_command)
            _values "scrape command" \\
                "apple-dictionary[Bulk scrape Apple Dictionary (macOS)]" \\
                "wordhippo[Bulk scrape WordHippo for synonyms/antonyms]" \\
                "free-dictionary[Bulk scrape FreeDictionary API]" \\
                "wiktionary-wholesale[Download complete Wiktionary dumps]" \\
                "sessions[List all scraping sessions]" \\
                "status[Show scraping status]" \\
                "resume[Resume a scraping session]" \\
                "delete[Delete a scraping session]" \\
                "cleanup[Clean up old sessions]" \\
                "--help[Show scrape help]"
            ;;
        scrape_args)
            case $line[2] in
                apple-dictionary|wordhippo|free-dictionary|wiktionary-wholesale)
                    _arguments \\
                        '--skip-existing[Skip words that already have data]' \\
                        '--include-existing[Include words that already have data]' \\
                        '--force-refresh[Force refresh existing data]' \\
                        '(-n --session-name)'{-n,--session-name}'[Name for this scraping session]:session name:' \\
                        '(-r --resume-session)'{-r,--resume-session}'[Resume from existing session ID]:session id:' \\
                        '(-c --max-concurrent)'{-c,--max-concurrent}'[Maximum concurrent operations]:number:' \\
                        '(-b --batch-size)'{-b,--batch-size}'[Words per batch]:number:' \\
                        '(-l --language)'{-l,--language}'[Language to scrape]:language:(en fr es de it)' \\
                        '--help[Show command help]'
                    ;;
                status|resume|delete)
                    # Complete with session IDs (would need actual session data)
                    _message "session ID"
                    ;;
            esac
            ;;
    esac
}

_floridify_lookup() {
    _arguments \\
        '1:word to lookup:' \\
        '--provider[Dictionary providers to use]:provider:(wiktionary oxford apple_dictionary merriam_webster free_dictionary wordhippo ai_fallback synthesis)' \\
        '(-l --language)'{-l,--language}'[Language code]:language:' \\
        '--no-ai[Disable AI synthesis]' \\
        '--force-refresh[Force refresh from providers]' \\
        '--help[Show lookup help]'
}

_floridify_search() {
    _arguments \\
        '1:search query:' \\
        '--help[Show search help]'
}

_floridify_config() {
    _values "config command" \\
        "show[Show current configuration]" \\
        "set[Set configuration value]" \\
        "keys[Manage API keys]" \\
        "--help[Show config help]"
}

_floridify_database() {
    _values "database command" \\
        "stats[Show database statistics]" \\
        "migrate[Run database migrations]" \\
        "cleanup[Clean up database]" \\
        "--help[Show database help]"
}

compdef _floridify floridify
"""

    return completion_script


@click.command()
@click.option(
    "--shell",
    type=click.Choice(["zsh", "bash"]),
    default="zsh",
    help="Shell to generate completion for",
)
def completion_command(shell: str) -> None:
    """Generate shell completion script for floridify."""
    if shell == "zsh":
        completion = generate_zsh_completion()
        click.echo(completion)
        click.echo("\n# To install, run:", err=True)
        click.echo(
            "# floridify completion --shell zsh > ~/.local/share/zsh/site-functions/_floridify",
            err=True,
        )
        click.echo("# Or add to your ~/.zshrc:", err=True)
        click.echo('# eval "$(floridify completion --shell zsh)"', err=True)
    else:
        click.echo("Bash completion not yet implemented", err=True)


if __name__ == "__main__":
    completion_command()
