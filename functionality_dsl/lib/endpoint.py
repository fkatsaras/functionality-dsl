from typing import List, Optional

from functionality_dsl.lib.pipeline import Pipeline


class PathParam:
    """
    Represents a path parameter for an endpoint method.

    Attributes:
        name: parameter name
        type: primitive type of the parameter
        required: whether it is required
    """
    def __init__(self, name: str, type: str, required: bool = False):
        self.name = name
        self.type = type
        self.required = required

    def __repr__(self):
        req = 'required' if self.required else 'optional'
        return f"<PathParam name={self.name!r} type={self.type!r} {req}>"


class EndpointMethod:
    """
    Represents a single HTTP method mapping to a Pipeline.

    Attributes:
        http_method: one of GET, POST, PUT, PATCH, DELETE
        pipeline: referenced Pipeline instance
    """
    def __init__(self, httpMethod: str, pipeline: Pipeline):
        self.http_method = httpMethod
        self.pipeline = pipeline

        allowed = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE'}
        if self.http_method not in allowed:
            raise ValueError(f"Invalid HTTP method: {self.http_method}. ")

    def __repr__(self):
        return f"<EndpointMethod {self.http_method} -> {self.pipeline.name!r}>"


class Endpoint:
    """
    Represents an API endpoint with path, transport, methods, and optional metadata.

    Attributes:
        path: URL path string
        transport: 'REST' or 'WS'
        version: optional version identifier
        description: optional description
        params: list of PathParam
        middleware: list of middleware FQN strings
        methods: list of EndpointMethod instances
    """
    def __init__(
        self,
        path: str,
        transport: str,
        version: Optional[str] = None,
        description: Optional[str] = None,
        params: Optional[List[PathParam]] = None,
        middleware: Optional[List[str]] = None,
        methods: Optional[List[EndpointMethod]] = None,
    ):
        self.path = path
        self.transport = transport
        self.version = version
        self.description = description
        self.params = params or []
        self.middleware = middleware or []
        self.methods = methods or []

        if self.transport not in {'REST', 'WS'}:
            raise ValueError(
                f"Invalid transport {self.transport!r}. Must be 'REST' or 'WS'."
            )
        if not self.methods:
            raise ValueError("Endpoint must have at least one method defined.")

    def __repr__(self):
        vers = f" version={self.version!r}" if self.version else ''
        desc = f" description={self.description!r}" if self.description else ''
        params = f" params={self.params!r}" if self.params else ''
        mw = f" middleware={self.middleware!r}" if self.middleware else ''
        return (
            f"<Endpoint path={self.path!r} transport={self.transport!r}{vers}{desc}"
            f"{params}{mw} methods={self.methods!r}>"
        )