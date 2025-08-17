class LiteratureCorpusMetadata(CorpusMetadata):
    """Literature-based corpus metadata."""

    literature_data_ids: list[PydanticObjectId] = Field(default_factory=list)
    authors: list[AuthorInfo] = Field(default_factory=list)
    periods: list[Period] = Field(default_factory=list)
    genres: list[Genre] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        data["corpus_type"] = CorpusType.LITERATURE
        super().__init__(**data)