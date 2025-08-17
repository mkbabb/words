class LanguageCorpusMetadata(CorpusMetadata):
    """Language-level master corpus metadata."""

    # Aggregated statistics
    total_documents: int = 0
    total_tokens: int = 0
    unique_sources: list[str] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        data["corpus_type"] = CorpusType.LANGUAGE
        data["is_master"] = True
        super().__init__(**data)
