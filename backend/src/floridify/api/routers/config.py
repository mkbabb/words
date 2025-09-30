"""Configuration management endpoints (read-only for API security)."""

from __future__ import annotations

from typing import Any

import toml
from fastapi import APIRouter, Depends, HTTPException, Path

from ...models.parameters import ConfigGetParams
from ...models.responses import ConfigResponse
from ...utils.logging import get_logger
from ...utils.paths import AUTH_DIR

logger = get_logger(__name__)
router = APIRouter()


def parse_config_get_params(
    section: str = "general",
    show_keys: bool = False,
) -> ConfigGetParams:
    """Parse config get parameters."""
    return ConfigGetParams(
        section=section,
        show_keys=show_keys,
    )


@router.get("/config", response_model=ConfigResponse)
async def get_configuration(
    params: ConfigGetParams = Depends(parse_config_get_params),
) -> ConfigResponse:
    """Get configuration (read-only).

    Returns configuration for all sections or a specific section.
    API keys are masked by default unless show_keys=true.

    Note: Write operations (set, edit, reset) are CLI-only for security.
    """
    try:
        config_file = AUTH_DIR / "config.toml"
        if not config_file.exists():
            raise HTTPException(status_code=404, detail="Configuration file not found")

        config_data = toml.load(config_file)

        # Mask sensitive keys unless explicitly requested
        masked_keys = []
        sections = {}

        for section_name, section_values in config_data.items():
            section_data = {}
            for key, value in section_values.items():
                value_str = str(value)

                # Mask API keys and sensitive values
                if not params.show_keys and any(
                    sensitive in key.lower() for sensitive in ["key", "token", "password", "secret"]
                ):
                    if value_str and len(value_str) > 6:
                        section_data[key] = value_str[:6] + "..." + value_str[-4:]
                    else:
                        section_data[key] = "***"
                    masked_keys.append(f"{section_name}.{key}")
                else:
                    section_data[key] = value

            sections[section_name] = section_data

        return ConfigResponse(
            sections=sections,
            masked_keys=masked_keys if not params.show_keys else None,
        )

    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {e!s}")


@router.get("/config/{key}", response_model=dict[str, Any])
async def get_config_value(
    key: str = Path(..., description="Configuration key"),
    params: ConfigGetParams = Depends(parse_config_get_params),
) -> dict[str, Any]:
    """Get a specific configuration value.

    Returns the value for a given key in the specified section.
    API keys are masked unless show_keys=true.
    """
    try:
        config_file = AUTH_DIR / "config.toml"
        if not config_file.exists():
            raise HTTPException(status_code=404, detail="Configuration file not found")

        config_data = toml.load(config_file)

        if params.section not in config_data:
            raise HTTPException(status_code=404, detail=f"Section not found: {params.section}")

        if key not in config_data[params.section]:
            raise HTTPException(
                status_code=404,
                detail=f"Configuration key not found: {params.section}.{key}",
            )

        value = config_data[params.section][key]

        # Mask sensitive values
        is_sensitive = any(
            sensitive in key.lower() for sensitive in ["key", "token", "password", "secret"]
        )

        if is_sensitive and not params.show_keys:
            if value and len(value) > 6:
                display_value = value[:6] + "..." + value[-4:]
            else:
                display_value = "***"
        else:
            display_value = value

        return {
            "section": params.section,
            "key": key,
            "value": display_value,
            "masked": is_sensitive and not params.show_keys,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get config value for {key}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config value: {e!s}")
