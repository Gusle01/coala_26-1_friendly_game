#!/usr/bin/env python3
"""친해지길 바라 보드게임 - Python CLI 버전 (B안).

Rules implemented:
- 팀 기반 플레이
- 활동 점수 = 기본 + 난이도 + 참여 인원 보너스(3인 이상)
- 누적 40점마다 던지기 기회 1회 획득
- 50칸 윷 레이스 트랙
- 잡히면 마지막 10칸 체크포인트로 복귀
- 윷/모는 추가 던지기 기회 제공
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

STORAGE_FILE = Path(__file__).with_name("state.json")

FINISH_POS = 50
CHECKPOINT_INTERVAL = 10
SCORE_PER_THROW = 40

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

YUT_OUTCOMES = [
    {"key": "do", "label": "도", "step": 1, "weight": 34, "extra_throw": 0},
    {"key": "gae", "label": "개", "step": 2, "weight": 26, "extra_throw": 0},
    {"key": "geol", "label": "걸", "step": 3, "weight": 17, "extra_throw": 0},
    {"key": "yut", "label": "윷", "step": 4, "weight": 11, "extra_throw": 1},
    {"key": "mo", "label": "모", "step": 5, "weight": 8, "extra_throw": 1},
    {"key": "backdo", "label": "빽도", "step": -1, "weight": 4, "extra_throw": 0},
]


@dataclass
class Team:
    id: str
    name: str
    score: int = 0
    mission_count: int = 0
    throw_chance: int = 0
    throw_granted_by_score: int = 0
    position: int = 0
    finished_at: Optional[str] = None
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
        self.finish_order: List[str] = []

    def save(self) -> None:
        payload = {
            "teams": [asdict(t) for t in self.teams],
            "logs": [asdict(l) for l in self.logs],
            "finish_order": self.finish_order,
        }
        STORAGE_FILE.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> "Game":
        game = cls()
        if not STORAGE_FILE.exists():
            return game

        try:
            payload = json.loads(STORAGE_FILE.read_text(encoding="utf-8"))
            for raw in payload.get("teams", []):
                team = Team(**raw)
                if not isinstance(team.throw_granted_by_score, int):
                    team.throw_granted_by_score = team.score // SCORE_PER_THROW
                game.teams.append(team)
            game.logs = [LogEntry(**l) for l in payload.get("logs", [])]
            game.finish_order = list(payload.get("finish_order", []))
        except Exception:
            # If state is broken, start clean.
            return cls()

        return game

    def add_log(self, text: str) -> None:
        self.logs.insert(0, LogEntry(at=datetime.now().isoformat(timespec="seconds"), text=text))
        self.logs = self.logs[:150]

    def _new_id(self) -> str:
        return f"team_{int(datetime.now().timestamp() * 1000)}_{random.randint(1000, 9999)}"

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

        if all(team.category_count[c] > 0 for c in CATEGORIES) and team.set_bonus_taken == 0:
            bonus += SET_BONUS_POINTS
            team.set_bonus_taken = 1

        for c in CATEGORIES:
            ready = team.category_count[c] // LINE_THRESHOLD
            if ready > team.line_bonus_taken[c]:
                gained = ready - team.line_bonus_taken[c]
                bonus += gained * LINE_BONUS_POINTS
                team.line_bonus_taken[c] = ready

        return bonus

    def apply_score_throw_milestone(self, team: Team) -> int:
        eligible = team.score // SCORE_PER_THROW
        if eligible <= team.throw_granted_by_score:
            return 0

        gained = eligible - team.throw_granted_by_score
        team.throw_granted_by_score = eligible
        team.throw_chance += gained
        return gained

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

        throws = self.apply_score_throw_milestone(team)

        detail = f" [{title.strip()}]" if title.strip() else ""
        bonus_text = f", 보너스 +{bonus}점" if bonus > 0 else ""
        throw_text = f", 던지기 +{throws}회" if throws > 0 else ""
        difficulty_label = DIFFICULTY_LABELS[difficulty]
        category_label = CATEGORY_LABELS[category]

        self.add_log(
            f"{team.name}{detail}: 활동 +{earned}점 (난이도:{difficulty_label}, 카테고리:{category_label}, 참여:{participant_count}명)"
            f"{bonus_text}{throw_text}"
        )
        self.save()
        return True, "활동이 반영되었습니다."

    def draw_yut(self) -> Dict[str, int | str]:
        total_weight = sum(o["weight"] for o in YUT_OUTCOMES)
        r = random.uniform(0, total_weight)
        acc = 0.0
        for outcome in YUT_OUTCOMES:
            acc += outcome["weight"]
            if r <= acc:
                return outcome
        return YUT_OUTCOMES[0]

    def ensure_finish(self, team: Team) -> None:
        if team.position >= FINISH_POS and not team.finished_at:
            team.position = FINISH_POS
            team.finished_at = datetime.now().isoformat(timespec="seconds")
            self.finish_order.append(team.id)
            team.score += 50
            throws = self.apply_score_throw_milestone(team)
            throw_text = f", 던지기 +{throws}회" if throws > 0 else ""
            self.add_log(f"{team.name} 완주! +50점{throw_text}")

    def capture_opponents(self, actor: Team) -> None:
        if actor.position <= 0 or actor.position >= FINISH_POS:
            return

        captured = [
            t
            for t in self.teams
            if t.id != actor.id and not t.finished_at and t.position == actor.position
        ]
        if not captured:
            return

        for enemy in captured:
            checkpoint = (enemy.position // CHECKPOINT_INTERVAL) * CHECKPOINT_INTERVAL
            enemy.position = checkpoint
            self.add_log(
                f"{actor.name}이(가) {enemy.name}을(를) 잡았습니다. {enemy.name}은(는) {checkpoint}칸 체크포인트로 복귀합니다."
            )

        gain = 30 * len(captured)
        actor.score += gain
        actor.throw_chance += len(captured)
        milestone_throws = self.apply_score_throw_milestone(actor)
        extra_milestone = f", 점수 마일스톤 던지기 +{milestone_throws}회" if milestone_throws > 0 else ""
        self.add_log(
            f"{actor.name}: 잡기 보너스 +{gain}점, 던지기 +{len(captured)}회{extra_milestone}"
        )

    def throw_yut(self, team_id: str) -> Tuple[bool, str]:
        team = self.find_team(team_id)
        if not team:
            return False, "유효하지 않은 팀입니다."
        if team.finished_at:
            return False, "이미 완주한 팀입니다."
        if team.throw_chance <= 0:
            return False, "던지기 기회가 없습니다. 활동으로 점수를 쌓아 40점 단위를 달성해주세요."

        yut = self.draw_yut()
        team.throw_chance -= 1
        team.position = max(0, team.position + int(yut["step"]))
        self.ensure_finish(team)

        if not team.finished_at:
            self.capture_opponents(team)

        if int(yut["extra_throw"]) > 0:
            team.throw_chance += int(yut["extra_throw"])

        step_text = f"+{yut['step']}" if int(yut["step"]) > 0 else str(yut["step"])
        extra_text = f", 추가 던지기 +{yut['extra_throw']}회" if int(yut["extra_throw"]) > 0 else ""
        msg = f"{team.name}: {yut['label']} ({step_text}칸){extra_text}"

        self.add_log(msg)
        self.save()
        return True, msg

    def reset(self) -> None:
        self.teams = []
        self.logs = []
        self.finish_order = []
        self.save()

    def sorted_teams(self) -> List[Team]:
        def sort_key(team: Team) -> Tuple[int, int, int, int]:
            finish_rank = self.finish_order.index(team.id) if team.id in self.finish_order else 10**9
            return (finish_rank, -team.score, -team.position, -team.mission_count)

        return sorted(self.teams, key=sort_key)

    def print_status(self) -> None:
        print("\n=== 현재 상태 ===")
        if not self.teams:
            print("등록된 팀이 없습니다.")
            return

        print(f"트랙: 0..{FINISH_POS}칸, 체크포인트 간격 {CHECKPOINT_INTERVAL}칸")
        print(f"던지기 마일스톤: 누적 {SCORE_PER_THROW}점마다 +1회")
        print("-")
        for idx, t in enumerate(self.sorted_teams(), start=1):
            finished = " [완주]" if t.finished_at else ""
            print(
                f"{idx}. {t.name} | 점수={t.score} | 위치={t.position}/{FINISH_POS} | "
                f"던지기={t.throw_chance} | 활동수={t.mission_count}{finished}"
            )
        print("")

    def print_logs(self, n: int = 15) -> None:
        print("\n=== 최근 로그 ===")
        if not self.logs:
            print("로그가 없습니다.\n")
            return
        for entry in self.logs[:n]:
            print(f"[{entry.at}] {entry.text}")
        print("")


def pick_team(game: Game, prompt: str) -> Optional[str]:
    if not game.teams:
        print("등록된 팀이 없습니다. 먼저 팀을 추가해주세요.")
        return None

    print("\n팀 목록:")
    for i, team in enumerate(game.teams, start=1):
        print(f"{i}. {team.name} (id={team.id})")

    raw = input(f"{prompt} (번호): ").strip()
    if not raw.isdigit():
        print("잘못된 입력입니다.")
        return None

    idx = int(raw)
    if idx < 1 or idx > len(game.teams):
        print("잘못된 선택입니다.")
        return None

    return game.teams[idx - 1].id


def record_activity_flow(game: Game) -> None:
    team_id = pick_team(game, "활동 팀 선택")
    if not team_id:
        return

    difficulty_raw = input("난이도 [쉬움/보통/어려움] (기본: 보통): ").strip()
    category_raw = input("카테고리 [대화/협동/도움/도전] (기본: 대화): ").strip()
    participant_raw = input("참여 인원 (기본: 2): ").strip() or "2"
    title = input("활동명 (선택): ").strip()

    if not participant_raw.isdigit():
        print("참여 인원은 양의 정수여야 합니다.")
        return

    difficulty_alias = {
        "": "medium",
        "쉬움": "easy",
        "보통": "medium",
        "어려움": "hard",
        "easy": "easy",
        "medium": "medium",
        "hard": "hard",
    }
    category_alias = {
        "": "talk",
        "대화": "talk",
        "협동": "teamplay",
        "도움": "help",
        "도전": "challenge",
        "talk": "talk",
        "teamplay": "teamplay",
        "help": "help",
        "challenge": "challenge",
    }
    difficulty = difficulty_alias.get(difficulty_raw.lower() if difficulty_raw.isascii() else difficulty_raw)
    category = category_alias.get(category_raw.lower() if category_raw.isascii() else category_raw)
    if not difficulty:
        print("난이도 입력이 잘못되었습니다.")
        return
    if not category:
        print("카테고리 입력이 잘못되었습니다.")
        return

    ok, msg = game.record_activity(
        team_id=team_id,
        difficulty=difficulty,
        category=category,
        participant_count=int(participant_raw),
        title=title,
    )
    print(msg)


def throw_yut_flow(game: Game) -> None:
    team_id = pick_team(game, "던질 팀 선택")
    if not team_id:
        return

    ok, msg = game.throw_yut(team_id)
    print(msg)


def main() -> None:
    game = Game.load()

    menu = """
=== 친해지길 바라 B안 (Python CLI) ===
1) 현재 상태 보기
2) 팀 추가
3) 활동 기록
4) 윷 던지기
5) 최근 로그 보기
6) 게임 초기화
0) 종료
"""

    while True:
        print(menu)
        choice = input("선택: ").strip()

        if choice == "1":
            game.print_status()
        elif choice == "2":
            name = input("팀 이름: ").strip()
            _, msg = game.add_team(name)
            print(msg)
        elif choice == "3":
            record_activity_flow(game)
        elif choice == "4":
            throw_yut_flow(game)
        elif choice == "5":
            game.print_logs()
        elif choice == "6":
            confirm = input("모든 데이터를 초기화할까요? [y/N]: ").strip().lower()
            if confirm == "y":
                game.reset()
                print("게임 초기화가 완료되었습니다.")
            else:
                print("취소되었습니다.")
        elif choice == "0":
            print("종료합니다.")
            break
        else:
            print("잘못된 메뉴입니다.")


if __name__ == "__main__":
    main()
