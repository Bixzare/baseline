"""Small local access probe through nba_api's documented endpoint interface."""

import os
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from nba_api.stats.endpoints.leaguegamelog import LeagueGameLog
from nba_api.stats.library.http import NBAStatsHTTP

from hoop.domains.nba.sources.policy import USER_AGENT, ProbeRequest, Response
from hoop.domains.nba.sources.validate import validate
from hoop.platform.provenance import Archive

HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}
BODY_LIMIT = 8 * 1024 * 1024


class NBAApiHistoryTransport:
    """Use the native client while preserving responses before its parser runs.

    This sequential diagnostic temporarily replaces the package's shared session.
    The native client buffers responses; this is not a production download limiter.
    """

    def __init__(self, archive: Archive, *, confirm_local_machine: bool) -> None:
        if not confirm_local_machine:
            raise ValueError("Confirm this is your own local computer")
        if (
            os.environ.get("GITHUB_ACTIONS") == "true"
            or os.environ.get("CI", "").lower() == "true"
            or "CODEX_PROXY_CERT" in os.environ
        ):
            raise ValueError("Historical stats requests are forbidden from cloud/CI runners")
        self.archive = archive
        self.parse_error: str | None = None
        self.frame_rows: int | None = None

    def get(self, url: str, timeout: float) -> Response:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "stats.nba.com":
            raise ValueError("Native probe only supports stats.nba.com over HTTPS")
        if parsed.path != "/stats/leaguegamelog":
            raise ValueError("Native probe only supports LeagueGameLog")
        parameters = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
        if parameters["PlayerOrTeam"] not in [["P"], ["T"]]:
            raise ValueError("Expected player or team history")
        self.parse_error = None
        self.frame_rows = None
        captured: Response | None = None

        def retain(response: Any, **kwargs: Any) -> None:
            nonlocal captured
            # Response hooks run before nba_api reads/parses the response text.
            body = response.content
            captured = Response(
                response.status_code,
                body[: BODY_LIMIT + 1],
                {key.lower(): value for key, value in response.headers.items()},
                complete=len(body) <= BODY_LIMIT,
            )
            self.archive.raw(captured.body)

        # Save the actual reference, without lazily creating a previous session.
        previous_session = NBAStatsHTTP._session
        with requests.Session() as session:
            session.max_redirects = 0
            session.hooks["response"].append(retain)
            NBAStatsHTTP.set_session(session)
            try:
                endpoint = LeagueGameLog(
                    season=parameters["Season"][0],
                    player_or_team_abbreviation=parameters["PlayerOrTeam"][0],
                    season_type_all_star=parameters["SeasonType"][0],
                    date_from_nullable=parameters["DateFrom"][0],
                    date_to_nullable=parameters["DateTo"][0],
                    headers=HEADERS.copy(),
                    proxy="",
                    timeout=timeout,
                )
                self.frame_rows = len(endpoint.league_game_log.get_data_frame())
            except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                if captured is None:
                    raise
                self.parse_error = type(error).__name__
            finally:
                NBAStatsHTTP.set_session(previous_session)
        if captured is None:
            raise RuntimeError("nba_api returned without an observed HTTP response")
        return captured

    def validate(self, body: bytes, request: ProbeRequest, now: datetime) -> dict[str, Any]:
        if self.parse_error is not None:
            raise ValueError(f"native_client_parse_failed: {self.parse_error}")
        return validate(body, request, now)
