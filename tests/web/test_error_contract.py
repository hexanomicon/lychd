"""Stable JSON errors shared by runtime behavior and generated transport types."""

from __future__ import annotations

from litestar import Litestar, get

from lychd.lib.exceptions import ApplicationError, exception_to_http_response


@get("/failure")
async def fail_with_application_error() -> None:
    """Raise the application-owned error translated by the production app."""
    raise ApplicationError(detail="deliberate failure")


def test_application_error_keeps_json_contract_even_in_debug_mode() -> None:
    from tests.web.conftest import AsgiClient

    app = Litestar(
        route_handlers=[fail_with_application_error],
        exception_handlers={ApplicationError: exception_to_http_response},
        debug=True,
    )
    response = AsgiClient(app).get("/failure")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status_code": 500,
        "detail": "Internal Server Error",
    }
