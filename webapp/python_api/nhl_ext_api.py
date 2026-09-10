"""
nhl_api.py
Lightweight Python client for the public NHL APIs.

Hosts:
  - https://api-web.nhle.com/v1
  - https://api.nhle.com/stats/rest/en
  - https://search.d3.nhle.com/api/v1

No API key is required for the public endpoints used here.

Install:
    pip install requests

Quick start:
    from nhl_api import NHLClient

    nhl = NHLClient()

    games = nhl.get_score("2026-09-06")
    standings = nhl.get_standings()
    game = nhl.get_game(2026020001)
    form = nhl.get_team_form("EDM", games=5)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

import requests


class NHLAPIError(RuntimeError):
    """Raised when an NHL API request fails."""


class NHLClient:
    WEB_BASE = "https://api-web.nhle.com/v1"
    STATS_BASE = "https://api.nhle.com/stats/rest/en"
    SEARCH_BASE = "https://search.d3.nhle.com/api/v1"

    def __init__(
        self,
        timeout: float = 20.0,
        retries: int = 3,
        session: Optional[requests.Session] = None,
    ):
        self.timeout = timeout
        self.retries = retries
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "nhl-api-python-client/1.0",
                "Accept": "application/json",
            }
        )

    # ---------- low-level HTTP ----------

    def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        last_error = None

        for attempt in range(self.retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < self.retries - 1:
                    continue

        raise NHLAPIError(
            f"Request failed: {url}. Last error: {last_error}"
        ) from last_error

    def _web(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._get(f"{self.WEB_BASE}/{path.lstrip('/')}", params)

    def _stats(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._get(f"{self.STATS_BASE}/{path.lstrip('/')}", params)

    def _search(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._get(f"{self.SEARCH_BASE}/{path.lstrip('/')}", params)

    # ---------- seasons / meta ----------

    def get_seasons(self) -> Any:
        """Return NHL season metadata."""
        return self._web("season")

    def get_latest_season(self) -> Optional[int]:
        """Return the latest season ID, e.g. 20252026."""
        data = self.get_seasons()
        if isinstance(data, list) and data:
            item = data[-1]
            return item.get("id") if isinstance(item, dict) else None
        if isinstance(data, dict):
            seasons = data.get("seasons") or data.get("data") or []
            if seasons:
                return seasons[-1].get("id")
        return None

    def get_teams(self) -> Any:
        """Return NHL team metadata from Stats API."""
        return self._stats("team")

    def get_team_by_id(self, team_id: int) -> Any:
        return self._stats(f"team/id/{team_id}")

    # ---------- schedule / scores ----------

    def get_score(self, day: Optional[str] = None) -> Any:
        """
        Scores for a date YYYY-MM-DD.
        If day is None, uses the NHL 'now' endpoint.
        """
        return self._web("score/now" if day is None else f"score/{day}")

    def get_schedule(self, day: Optional[str] = None) -> Any:
        """League schedule for a date."""
        return self._web("schedule/now" if day is None else f"schedule/{day}")

    def get_schedule_calendar(self, day: Optional[str] = None) -> Any:
        """Schedule calendar metadata for a date."""
        return self._web(
            "schedule-calendar/now" if day is None else f"schedule-calendar/{day}"
        )

    def get_team_schedule(
        self,
        team: str,
        season: Optional[int] = None,
    ) -> Any:
        """
        Get a team's season schedule.
        Uses the current-season endpoint when season is omitted.
        """
        team = team.upper()
        if season is None:
            return self._web(f"club-schedule-season/{team}/now")
        return self._web(f"club-schedule-season/{team}/{season}")

    def get_team_month(
        self,
        team: str,
        year_month: Optional[str] = None,
    ) -> Any:
        """Get a team's monthly schedule, e.g. 2026-10."""
        team = team.upper()
        if year_month:
            return self._web(f"club-schedule/{team}/month/{year_month}")
        return self._web(f"club-schedule/{team}/month/now")

    def get_team_week(
        self,
        team: str,
        day: Optional[str] = None,
    ) -> Any:
        """Get a team's weekly schedule."""
        team = team.upper()
        if day:
            return self._web(f"club-schedule/{team}/week/{day}")
        return self._web(f"club-schedule/{team}/week/now")

    # ---------- standings ----------

    def get_standings(self, day: Optional[str] = None) -> Any:
        """League standings for today or a specific date."""
        return self._web("standings/now" if day is None else f"standings/{day}")

    def get_standings_seasons(self) -> Any:
        return self._web("standings-season")

    # ---------- gamecenter ----------

    def get_game(self, game_id: int) -> Any:
        """Full game landing/gamecenter payload."""
        return self._web(f"gamecenter/{game_id}/landing")

    def get_boxscore(self, game_id: int) -> Any:
        return self._web(f"gamecenter/{game_id}/boxscore")

    def get_play_by_play(self, game_id: int) -> Any:
        return self._web(f"gamecenter/{game_id}/play-by-play")

    def get_game_right_rail(self, game_id: int) -> Any:
        return self._web(f"gamecenter/{game_id}/right-rail")

    def get_game_meta(self, game_id: int) -> Any:
        return self._web(f"meta/game/{game_id}")

    def get_shift_charts(self, game_id: int) -> Any:
        return self._stats("shiftcharts", {"cayenneExp": f"gameId={game_id}"})

    # ---------- teams ----------

    def get_team_stats(
        self,
        team_id: Optional[int] = None,
        season_id: Optional[int] = None,
        game_type_id: int = 2,
        report: str = "summary",
        limit: int = 100,
    ) -> Any:
        """
        Query team statistics.

        Example:
            get_team_stats(team_id=25, season_id=20252026)
        """
        expressions = []
        if season_id is not None:
            expressions.append(f"seasonId={season_id}")
        if game_type_id is not None:
            expressions.append(f"gameTypeId={game_type_id}")
        if team_id is not None:
            expressions.append(f"teamId={team_id}")

        params = {
            "cayenneExp": " and ".join(expressions),
            "limit": limit,
        }
        return self._stats(f"team/{report}", params)

    def get_team_stats_raw(
        self,
        report: str = "summary",
        *,
        cayenne_exp: Optional[str] = None,
        sort: Optional[str] = None,
        direction: str = "desc",
        start: int = 0,
        limit: int = 100,
        **extra: Any,
    ) -> Any:
        """Generic Stats API team report."""
        params = dict(extra)
        if cayenne_exp:
            params["cayenneExp"] = cayenne_exp
        if sort:
            params["sort"] = sort
            params["dir"] = direction
        params["start"] = start
        params["limit"] = limit
        return self._stats(f"team/{report}", params)

    # ---------- players ----------

    def get_player(self, player_id: int) -> Any:
        return self._web(f"player/{player_id}/landing")

    def get_player_game_log(
        self,
        player_id: int,
        season: Optional[int] = None,
        game_type: int = 2,
    ) -> Any:
        if season is None:
            return self._web(f"player/{player_id}/game-log/now")
        return self._web(f"player/{player_id}/game-log/{season}/{game_type}")

    def get_roster(
        self,
        team: str,
        season: Optional[int] = None,
    ) -> Any:
        team = team.upper()
        if season is None:
            return self._web(f"roster/{team}/current")
        return self._web(f"roster/{team}/{season}")

    def get_roster_seasons(self, team: str) -> Any:
        return self._web(f"roster-season/{team.upper()}")

    # ---------- player / goalie stats ----------

    def get_skaters(
        self,
        season_id: Optional[int] = None,
        game_type_id: int = 2,
        *,
        sort: str = "points",
        direction: str = "desc",
        limit: int = 100,
        start: int = 0,
        team_id: Optional[int] = None,
        cayenne_exp: Optional[str] = None,
        report: str = "summary",
        **extra: Any,
    ) -> Any:
        """Query skater statistics."""
        if cayenne_exp is None:
            parts = []
            if season_id is not None:
                parts.append(f"seasonId={season_id}")
            if game_type_id is not None:
                parts.append(f"gameTypeId={game_type_id}")
            if team_id is not None:
                parts.append(f"teamId={team_id}")
            cayenne_exp = " and ".join(parts)

        params = {
            "cayenneExp": cayenne_exp,
            "sort": sort,
            "dir": direction,
            "start": start,
            "limit": limit,
        }
        params.update(extra)
        return self._stats(f"skater/{report}", params)

    def get_goalies(
        self,
        season_id: Optional[int] = None,
        game_type_id: int = 2,
        *,
        sort: str = "wins",
        direction: str = "desc",
        limit: int = 100,
        start: int = 0,
        team_id: Optional[int] = None,
        cayenne_exp: Optional[str] = None,
        report: str = "summary",
        **extra: Any,
    ) -> Any:
        """Query goalie statistics."""
        if cayenne_exp is None:
            parts = []
            if season_id is not None:
                parts.append(f"seasonId={season_id}")
            if game_type_id is not None:
                parts.append(f"gameTypeId={game_type_id}")
            if team_id is not None:
                parts.append(f"teamId={team_id}")
            cayenne_exp = " and ".join(parts)

        params = {
            "cayenneExp": cayenne_exp,
            "sort": sort,
            "dir": direction,
            "start": start,
            "limit": limit,
        }
        params.update(extra)
        return self._stats(f"goalie/{report}", params)

    def get_players(
        self,
        *,
        cayenne_exp: Optional[str] = None,
        sort: str = "lastName",
        direction: str = "asc",
        limit: int = 100,
        start: int = 0,
        **extra: Any,
    ) -> Any:
        params = {
            "sort": sort,
            "dir": direction,
            "start": start,
            "limit": limit,
        }
        if cayenne_exp:
            params["cayenneExp"] = cayenne_exp
        params.update(extra)
        return self._stats("players", params)

    def get_skaters_raw(
        self,
        report: str = "summary",
        *,
        cayenne_exp: Optional[str] = None,
        sort: Optional[str] = None,
        direction: str = "desc",
        start: int = 0,
        limit: int = 100,
        **extra: Any,
    ) -> Any:
        params = dict(extra)
        if cayenne_exp:
            params["cayenneExp"] = cayenne_exp
        if sort:
            params["sort"] = sort
            params["dir"] = direction
        params["start"] = start
        params["limit"] = limit
        return self._stats(f"skater/{report}", params)

    def get_goalies_raw(
        self,
        report: str = "summary",
        *,
        cayenne_exp: Optional[str] = None,
        sort: Optional[str] = None,
        direction: str = "desc",
        start: int = 0,
        limit: int = 100,
        **extra: Any,
    ) -> Any:
        params = dict(extra)
        if cayenne_exp:
            params["cayenneExp"] = cayenne_exp
        if sort:
            params["sort"] = sort
            params["dir"] = direction
        params["start"] = start
        params["limit"] = limit
        return self._stats(f"goalie/{report}", params)

    def get_skater_leaders(self, attribute: str = "points") -> Any:
        return self._stats(f"leaders/skaters/{attribute}")

    def get_goalie_leaders(self, attribute: str = "wins") -> Any:
        return self._stats(f"leaders/goalies/{attribute}")

    # ---------- search ----------

    def search(self, query: str, *, culture: str = "en-us") -> Any:
        """Search NHL players/teams through NHL's search service."""
        return self._search(
            "search",
            {
                "culture": culture,
                "q": query,
            },
        )

    # ---------- convenience analytics ----------

    @staticmethod
    def _games_from_payload(payload: Any) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        return payload.get("games") or []

    @staticmethod
    def _team_abbrev(team_obj: Any) -> Optional[str]:
        if isinstance(team_obj, dict):
            return team_obj.get("abbrev")
        return None

    def get_team_form(
        self,
        team: str,
        games: int = 5,
        season: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Return a compact recent-form summary for a team.

        Uses the team's season schedule and then fetches boxscores only for
        completed games, newest first.
        """
        team = team.upper()
        payload = self.get_team_schedule(team, season)
        all_games = payload.get("games", []) if isinstance(payload, dict) else []

        completed = [
            g for g in all_games
            if g.get("gameState") in {"OFF", "FINAL"}
        ]

        completed.sort(
            key=lambda x: x.get("startTimeUTC", ""),
            reverse=True,
        )
        selected = completed[:games]

        results = []
        wins = losses = ot_losses = goals_for = goals_against = 0

        for game in selected:
            home = game.get("homeTeam", {})
            away = game.get("awayTeam", {})
            is_home = home.get("abbrev") == team

            gf = (home if is_home else away).get("score")
            ga = (away if is_home else home).get("score")

            if gf is None or ga is None:
                continue

            gf = int(gf)
            ga = int(ga)
            goals_for += gf
            goals_against += ga

            # NHL result convention: a team with fewer goals in an OT/SO game
            # receives an OTL rather than a regulation loss.
            went_ot = bool(game.get("periodDescriptor", {}).get("periodType") in {"OT", "SO"})
            if gf > ga:
                result = "W"
                wins += 1
            elif went_ot:
                result = "OTL"
                ot_losses += 1
            else:
                result = "L"
                losses += 1

            results.append(
                {
                    "game_id": game.get("id"),
                    "date": game.get("startTimeUTC"),
                    "opponent": (away if is_home else home).get("abbrev"),
                    "home": is_home,
                    "gf": gf,
                    "ga": ga,
                    "result": result,
                }
            )

        n = len(results)
        return {
            "team": team,
            "games_requested": games,
            "games_found": n,
            "record": {
                "wins": wins,
                "losses": losses,
                "ot_losses": ot_losses,
            },
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goals_for_per_game": round(goals_for / n, 3) if n else 0.0,
            "goals_against_per_game": round(goals_against / n, 3) if n else 0.0,
            "results": results,
        }

    def get_h2h(
        self,
        team_a: str,
        team_b: str,
        season: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find completed head-to-head games from team_a's season schedule.
        """
        team_a = team_a.upper()
        team_b = team_b.upper()

        payload = self.get_team_schedule(team_a, season)
        games = payload.get("games", []) if isinstance(payload, dict) else []

        h2h = []
        for g in games:
            if g.get("gameState") not in {"OFF", "FINAL"}:
                continue

            home = g.get("homeTeam", {})
            away = g.get("awayTeam", {})

            pair = {home.get("abbrev"), away.get("abbrev")}
            if pair != {team_a, team_b}:
                continue

            is_home = home.get("abbrev") == team_a
            gf = (home if is_home else away).get("score")
            ga = (away if is_home else home).get("score")

            h2h.append(
                {
                    "game_id": g.get("id"),
                    "date": g.get("startTimeUTC"),
                    "home": home.get("abbrev"),
                    "away": away.get("abbrev"),
                    "home_score": home.get("score"),
                    "away_score": away.get("score"),
                    "team_a_score": gf,
                    "team_b_score": ga,
                }
            )

        h2h.sort(key=lambda x: x.get("date", ""), reverse=True)
        return h2h

    def get_match_analysis(
        self,
        game_id: int,
        *,
        form_games: int = 5,
        include_pbp: bool = False,
    ) -> Dict[str, Any]:
        """
        Build a compact analysis payload suitable for an AI prompt.
        """
        landing = self.get_game(game_id)
        boxscore = self.get_boxscore(game_id)

        home = landing.get("homeTeam", {}) if isinstance(landing, dict) else {}
        away = landing.get("awayTeam", {}) if isinstance(landing, dict) else {}

        home_abbr = home.get("abbrev")
        away_abbr = away.get("abbrev")

        result = {
            "game_id": game_id,
            "game": {
                "date": landing.get("startTimeUTC"),
                "state": landing.get("gameState"),
                "home": home_abbr,
                "away": away_abbr,
                "home_score": home.get("score"),
                "away_score": away.get("score"),
            },
            "home_form": self.get_team_form(home_abbr, form_games)
            if home_abbr else None,
            "away_form": self.get_team_form(away_abbr, form_games)
            if away_abbr else None,
            "boxscore": boxscore,
        }

        if home_abbr and away_abbr:
            result["h2h"] = self.get_h2h(home_abbr, away_abbr)

        if include_pbp:
            result["play_by_play"] = self.get_play_by_play(game_id)

        return result


# ---------- small functional API ----------

_default_client = NHLClient()


def get_score(day: Optional[str] = None) -> Any:
    return _default_client.get_score(day)


def get_schedule(day: Optional[str] = None) -> Any:
    return _default_client.get_schedule(day)


def get_standings(day: Optional[str] = None) -> Any:
    return _default_client.get_standings(day)


def get_game(game_id: int) -> Any:
    return _default_client.get_game(game_id)


def get_boxscore(game_id: int) -> Any:
    return _default_client.get_boxscore(game_id)


def get_play_by_play(game_id: int) -> Any:
    return _default_client.get_play_by_play(game_id)


def get_team_schedule(team: str, season: Optional[int] = None) -> Any:
    return _default_client.get_team_schedule(team, season)


def get_team_form(
    team: str,
    games: int = 5,
    season: Optional[int] = None,
) -> Dict[str, Any]:
    return _default_client.get_team_form(team, games, season)


def get_h2h(
    team_a: str,
    team_b: str,
    season: Optional[int] = None,
) -> List[Dict[str, Any]]:
    return _default_client.get_h2h(team_a, team_b, season)


def get_player(player_id: int) -> Any:
    return _default_client.get_player(player_id)


def get_roster(team: str, season: Optional[int] = None) -> Any:
    return _default_client.get_roster(team, season)


def get_skaters(**kwargs: Any) -> Any:
    return _default_client.get_skaters(**kwargs)


def get_goalies(**kwargs: Any) -> Any:
    return _default_client.get_goalies(**kwargs)


if __name__ == "__main__":
    # Simple smoke test:
    client = NHLClient()
    print(client.get_score())
