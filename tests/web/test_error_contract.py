"""Stable JSON errors shared by runtime behavior and generated transport types."""

from __future__ import annotations

from advanced_alchemy.exceptions import NotFoundError, RepositoryError
from litestar import Litestar, get

from lychd.lib.exceptions import ApplicationError, exception_to_http_response


@get("/failure")
async def fail_with_application_error() -> None:
    """Raise the application-owned error translated by the production app."""
    raise ApplicationError(detail="deliberate failure")


@get("/repository-failure")
async def fail_with_repository_error() -> None:
    """Raise a repository failure carrying hostile driver and wrapper details."""
    raise RepositoryError(detail="repository detail: prompt='private'") from RuntimeError(
        "driver SQL params: password='supersecret'"
    )


@get("/missing")
async def fail_with_not_found_error() -> None:
    """Raise an explicit absence whose internal cause must remain private."""
    private_detail = "wrapper-private"
    raise NotFoundError(private_detail, detail="Requested row was not found.") from RuntimeError(
        "driver SQL params: password='supersecret'"
    )


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


def test_repository_error_is_a_generic_server_failure_without_causal_detail() -> None:
    from tests.web.conftest import AsgiClient

    app = Litestar(
        route_handlers=[fail_with_repository_error],
        exception_handlers={RepositoryError: exception_to_http_response},
        debug=True,
    )
    response = AsgiClient(app).get("/repository-failure")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status_code": 500,
        "detail": "Internal Server Error",
    }
    assert "supersecret" not in response.text
    assert "private" not in response.text


def test_not_found_error_keeps_its_explicit_detail_without_causal_detail() -> None:
    from tests.web.conftest import AsgiClient

    app = Litestar(
        route_handlers=[fail_with_not_found_error],
        exception_handlers={RepositoryError: exception_to_http_response},
        debug=True,
    )
    response = AsgiClient(app).get("/missing")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status_code": 404,
        "detail": "Requested row was not found.",
    }
    assert "supersecret" not in response.text
    assert "wrapper-private" not in response.text
