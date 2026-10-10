"""The HTTP contract: every route, parameter and response model as FastAPI publishes it."""
from fastapi.routing import APIRoute


def test_openapi_schema(api_app, snapshot):
    snapshot("openapi", api_app.openapi())


def test_route_table(api_app, snapshot):
    routes = []
    for route in api_app.routes:
        if isinstance(route, APIRoute):
            routes.append({
                "path": route.path,
                "methods": sorted(route.methods),
                "endpoint": f"{route.endpoint.__module__}.{route.endpoint.__name__}",
                "status_code": route.status_code,
                "response_model": getattr(route.response_model, "__name__", str(route.response_model)),
                "tags": list(route.tags),
            })
    snapshot("route_table", sorted(routes, key=lambda r: (r["path"], r["methods"])))


def test_middleware(api_app, snapshot):
    snapshot("middleware", [
        {"class": m.cls.__name__, "options": {k: v for k, v in sorted(m.kwargs.items())}}
        for m in api_app.user_middleware
    ])
