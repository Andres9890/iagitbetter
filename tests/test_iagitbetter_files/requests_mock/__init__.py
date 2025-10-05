"""Minimal stub implementation of the :mod:`requests_mock` package used in tests.

The real ``requests-mock`` dependency is not available in this execution
environment, so we provide a tiny subset that mimics the API surface consumed
by the tests.  The stub supports registering responses for different HTTP
methods and transparently intercepts calls made through ``requests``.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, Optional, Tuple
from unittest.mock import patch

import requests


@dataclass
class _MockResponse:
    """Very small substitute for :class:`requests.Response`."""

    status_code: int = 200
    _json_data: Any = None
    text: Optional[str] = None
    content: Optional[bytes] = None
    headers: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.headers is None:
            self.headers = {}
        if self.content is None:
            if self.text is not None:
                self.content = self.text.encode("utf-8")
            else:
                self.content = b""
        if self.text is None:
            try:
                self.text = self.content.decode("utf-8")
            except Exception:
                self.text = ""

        # Provide a minimal file-like interface similar to ``requests.Response.raw``
        class _RawStream(BytesIO):
            def __init__(self, data: bytes) -> None:
                super().__init__(data)
                self.decode_content = False

        self.raw = _RawStream(self.content)

    def json(self) -> Any:
        if self._json_data is None:
            raise ValueError("No JSON data set for this mock response")
        return self._json_data

    def raise_for_status(self) -> None:
        if 400 <= self.status_code:
            http_error = requests.HTTPError(f"{self.status_code} Server Error")
            http_error.response = self  # type: ignore[attr-defined]
            raise http_error

    def clone(self) -> "_MockResponse":
        return _MockResponse(
            status_code=self.status_code,
            _json_data=self._json_data,
            text=self.text,
            content=bytes(self.content or b""),
            headers=dict(self.headers or {}),
        )


class Mocker:
    """Context manager / decorator compatible mock for ``requests`` calls."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._responses: Dict[Tuple[str, str], _MockResponse] = {}
        self._patcher = patch(
            "requests.sessions.Session.request",
            self._make_request_handler(),
        )

    # -- registration helpers -------------------------------------------------
    def get(self, url: str, **kwargs: Any) -> None:
        self._register("GET", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> None:
        self._register("PUT", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> None:
        self._register("POST", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> None:
        self._register("DELETE", url, **kwargs)

    def _register(self, method: str, url: str, **kwargs: Any) -> None:
        response = _MockResponse(
            status_code=kwargs.pop("status_code", 200),
            _json_data=kwargs.pop("json", None),
            text=kwargs.pop("text", None),
            content=kwargs.pop("content", None),
            headers=kwargs.pop("headers", None),
        )
        if kwargs:
            raise TypeError(
                f"Unsupported arguments for mock response: {sorted(kwargs)}"
            )
        self._responses[(method.upper(), url)] = response

    # -- context manager / decorator plumbing ---------------------------------
    def __enter__(self) -> "Mocker":
        self._responses.clear()
        self._patcher.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._patcher.stop()
        self._responses.clear()

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            with self as mocker:
                return func(*args, mocker, **kwargs)

        return wrapper

    # -- patched request handler ---------------------------------------------
    def _make_request_handler(self):
        def handler(
            session: requests.Session, method: str, url: str, **kwargs: Any
        ) -> _MockResponse:
            key = (method.upper(), url)
            if key not in self._responses:
                raise AssertionError(f"Unexpected {method.upper()} request to {url}")
            return self._responses[key].clone()

        return handler


__all__ = ["Mocker"]
