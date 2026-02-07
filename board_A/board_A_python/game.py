#!/usr/bin/env python3
"""친해지길 바라 A안 - 점수 레이스 로직 (Python)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from random import randint
from typing import Dict, List, Optional, Tuple

STORAGE_FILE = Path(__file__).with_name("state.json")

BASE_POINTS = 10
DIFFICULTY_POINTS = {"easy": 10, "medium": 20, "hard": 30}
DIFFICULTY_LABELS = {"easy": "쉬움", "medium": "보통", "hard": "어려움"}

TEAM_MEMBER_BONUS_POINTS = 20
TEAM_MEMBER_BONUS_START = 3

SET_BONUS_POINTS = 40
LINE_BONUS_POINTS = 25
LINE_THRESHOLD = 3

CATEGORIES = ["talk", "teamplay", "help", "challenge"]
CATEGORY_LABELS = {"talk": "대화", "teamplay": "협동", "help": "도움", "challenge": "도전"}


@dataclass
class Team:
    id: str
    name: str
    score: int = 0
    mission_count: int = 0
    category_count: Dict[str, int] = None
    set_bonus_taken: int = 0
    line_bonus_taken: Dict[str, int] = None

    def __post_init__(self) -> None:
        if self.category_count is None:
            self.category_count = {c: 0 for c in CATEGORIES}
        if self.line_bonus_taken is None:
            self.line_bonus_taken = {c: 0 for c in CATEGORIES}


@dataclass
class LogEntry:
    at: str
    text: str


class Game:
    def __init__(self) -> None:
        self.teams: List[Team] = []
        self.logs: List[LogEntry] = []

    def save(self) -> None:
        payload = {
            "teams": [asdict(t) for t in self.teams],
            "logs": [asdict(l) for l in self.logs],
        }
        STORAGE_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> "Game":
        game = cls()
        if not STORAGE_FILE.exists():
            return game
        try:
            payload = json.loads(STORAGE_FILE.read_text(encoding="utf-8"))
            game.teams = [Team(**item) for item in payload.get("teams", [])]
            game.logs = [LogEntry(**item) for item in payload.get("logs", [])]
        except Exception:
            return cls()
        return game

    def _new_id(self) -> str:
        millis = int(datetime.now().timestamp() * 1000)
        return f"team_{millis}_{randint(1000, 9999)}"

    def add_log(self, text: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        self.logs.insert(0, LogEntry(at=now, text=text))
        self.logs = self.logs[:120]

    def add_team(self, name: str) -> Tuple[bool, str]:
        name = name.strip()
        if not name:
            return False, "팀 이름을 입력해주세요."
        if any(t.name == name for t in self.teams):
            return False, "이미 같은 팀 이름이 있습니다."

        self.teams.append(Team(id=self._new_id(), name=name))
        self.add_log(f"팀 등록: {name}")
        self.save()
        return True, f"팀이 추가되었습니다: {name}"

    def find_team(self, team_id: str) -> Optional[Team]:
        for team in self.teams:
            if team.id == team_id:
                return team
        return None

    def compute_bonus(self, team: Team) -> int:
        bonus = 0

        done_all = all(team.category_count[c] > 0 for c in CATEGORIES)
        if done_all and team.set_bonus_taken == 0:
            bonus += SET_BONUS_POINTS
            team.set_bonus_taken = 1

        for cat in CATEGORIES:
            ready = team.category_count[cat] // LINE_THRESHOLD
            if ready > team.line_bonus_taken[cat]:
                gained = ready - team.line_bonus_taken[cat]
                bonus += gained * LINE_BONUS_POINTS
                team.line_bonus_taken[cat] = ready

        return bonus

    def record_activity(
        self,
        team_id: str,
        difficulty: str,
        category: str,
        participant_count: int,
        title: str,
    ) -> Tuple[bool, str]:
        team = self.find_team(team_id)
        if not team:
            return False, "유효하지 않은 팀입니다."
        if difficulty not in DIFFICULTY_POINTS:
            return False, "유효하지 않은 난이도입니다."
        if category not in CATEGORIES:
            return False, "유효하지 않은 카테고리입니다."
        if participant_count < 1:
            return False, "참여 인원은 1명 이상이어야 합니다."

        extra_members = max(0, participant_count - (TEAM_MEMBER_BONUS_START - 1))
        member_bonus = extra_members * TEAM_MEMBER_BONUS_POINTS

        earned = BASE_POINTS + DIFFICULTY_POINTS[difficulty] + member_bonus
        team.score += earned
        team.mission_count += 1
        team.category_count[category] += 1

        bonus = self.compute_bonus(team)
        if bonus > 0:
            team.score += bonus

        detail = f" [{title.strip()}]" if title.strip() else ""
        msg = (
            f"{team.name}{detail}: 활동 +{earned}점 "
            f"(난이도:{DIFFICULTY_LABELS[difficulty]}, 카테고리:{CATEGORY_LABELS[category]}, 참여:{participant_count}명)"
        )
        if bonus > 0:
            msg += f" + 보너스 {bonus}점"

        self.add_log(msg)
        self.save()
        return True, "활동이 반영되었습니다."

    def reset(self) -> None:
        self.teams = []
        self.logs = []
        self.save()

    def sorted_teams(self) -> List[Team]:
        return sorted(self.teams, key=lambda t: (-t.score, -t.mission_count, t.name))
