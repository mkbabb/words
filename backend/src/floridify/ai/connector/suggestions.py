"""Connector mixin for suggestions: query validation and word suggestions."""

from ...utils.logging import get_logger
from ..models import (
    QueryValidationResponse,
    WordSuggestionResponse,
)

logger = get_logger(__name__)


class SuggestionsMixin:
    """Mixin providing suggestion methods for OpenAIConnector."""

    async def validate_query(
        self,
        query: str,
    ) -> QueryValidationResponse:
        """Validate if query seeks word suggestions.

        Args:
            query: User's search query

        Returns:
            QueryValidationResponse with validation result

        """
        prompt = self.prompt_manager.render("misc/query_validation", query=query)

        result = await self._make_structured_request(
            prompt,
            QueryValidationResponse,
            task_name="validate_query",
        )
        logger.info(f"Query validation: {result.is_valid} - {result.reason}")
        return result

    async def suggest_words(
        self,
        query: str,
        count: int = 10,
    ) -> WordSuggestionResponse:
        """Generate word suggestions from descriptive query.

        Args:
            query: Descriptive query for word suggestions
            count: Number of suggestions to generate

        Returns:
            WordSuggestionResponse with ranked suggestions

        """
        prompt = self.prompt_manager.render(
            "misc/word_suggestion",
            query=query,
            count=count,
        )

        result = await self._make_structured_request(
            prompt,
            WordSuggestionResponse,
            task_name="suggest_words",
        )
        logger.info(f"Generated {len(result.suggestions)} word suggestions")
        return result
