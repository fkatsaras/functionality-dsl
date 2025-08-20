
class Datasource:
    """
    Represents a data source configuration.

    Attributes:
        name: Identifier of the datasource.
        kind: Type of datasource, e.g., 'SQL' or 'NOSQL'.
        uri: Connection URI/string for the datasource.
    """
    def __init__(
        self,
        name: str,
        kind: str,
        uri: str,
    ):
        self.name = name
        self.kind = kind
        self.uri = uri

        allowed_kinds = {'SQL', 'NOSQL'}
        if self.kind not in allowed_kinds:
            raise ValueError(
                f"Invalid datasource kind: {self.kind!r}. Must be one of {allowed_kinds}."
            )

    def __repr__(self):
        return (
            f"<Datasource name={self.name!r} kind={self.kind!r} uri={self.uri!r}>"
        )
