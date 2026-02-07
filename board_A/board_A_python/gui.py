#!/usr/bin/env python3
"""친해지길 바라 A안 - 점수 레이스 GUI(Tkinter)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from game import (
    CATEGORIES,
    CATEGORY_LABELS,
    DIFFICULTY_LABELS,
    DIFFICULTY_POINTS,
    Game,
)


class FriendlyScoreRaceGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("친해지길 바라 A안 - 점수 레이스 GUI")
        self.root.geometry("1240x780")

        self.game = Game.load()

        self.team_name_var = tk.StringVar()
        self.activity_team_var = tk.StringVar()
        self.difficulty_var = tk.StringVar(value="보통")
        self.category_var = tk.StringVar(value="대화")
        self.participant_var = tk.StringVar(value="2")
        self.activity_title_var = tk.StringVar()

        self.team_name_to_id: dict[str, str] = {}
        self.difficulty_label_to_key = {v: k for k, v in DIFFICULTY_LABELS.items()}
        self.category_label_to_key = {v: k for k, v in CATEGORY_LABELS.items()}

        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)

        header = ttk.Label(outer, text="친해지길 바라 A안 - 점수 레이스", font=("Helvetica", 18, "bold"))
        header.pack(anchor="w")

        subtitle = ttk.Label(
            outer,
            text="규칙: 기본 10 + 난이도 + (3명 이상 인원 보너스), 세트/라인 보너스, 점수 레이스",
        )
        subtitle.pack(anchor="w", pady=(2, 10))

        top = ttk.Frame(outer)
        top.pack(fill="x")

        self._build_team_box(top)
        self._build_activity_box(top)

        middle = ttk.Frame(outer)
        middle.pack(fill="both", expand=True, pady=(10, 0))

        self._build_race_board(middle)
        self._build_ranking_box(middle)

        bottom = ttk.Frame(outer)
        bottom.pack(fill="both", expand=True, pady=(10, 0))

        self._build_log_box(bottom)
        self._build_manage_box(bottom)

    def _build_team_box(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="팀 등록", padding=10)
        frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ttk.Label(frame, text="팀 이름").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.team_name_var).grid(row=1, column=0, sticky="ew")
        ttk.Button(frame, text="추가", command=self.on_add_team).grid(row=1, column=1, padx=(8, 0))

        frame.columnconfigure(0, weight=1)

    def _build_activity_box(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="활동 기록", padding=10)
        frame.pack(side="left", fill="both", expand=True, padx=(8, 0))

        ttk.Label(frame, text="활동 팀").grid(row=0, column=0, sticky="w")
        self.activity_team_combo = ttk.Combobox(frame, textvariable=self.activity_team_var, state="readonly")
        self.activity_team_combo.grid(row=1, column=0, sticky="ew")

        ttk.Label(frame, text="참여 인원").grid(row=0, column=1, sticky="w", padx=(8, 0))
        ttk.Entry(frame, textvariable=self.participant_var, width=8).grid(row=1, column=1, padx=(8, 0), sticky="w")

        ttk.Label(frame, text="난이도").grid(row=0, column=2, sticky="w", padx=(8, 0))
        ttk.Combobox(
            frame,
            textvariable=self.difficulty_var,
            values=[DIFFICULTY_LABELS[k] for k in DIFFICULTY_POINTS.keys()],
            state="readonly",
            width=10,
        ).grid(row=1, column=2, padx=(8, 0), sticky="w")

        ttk.Label(frame, text="카테고리").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(
            frame,
            textvariable=self.category_var,
            values=[CATEGORY_LABELS[k] for k in CATEGORIES],
            state="readonly",
            width=12,
        ).grid(row=3, column=0, sticky="w")

        ttk.Label(frame, text="활동명 (선택)").grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Entry(frame, textvariable=self.activity_title_var).grid(row=3, column=1, columnspan=2, padx=(8, 0), sticky="ew")

        ttk.Button(frame, text="반영", command=self.on_record_activity).grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)

    def _build_race_board(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="점수 레이스", padding=8)
        frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.race_canvas = tk.Canvas(frame, bg="#f7f1e2", highlightthickness=0)
        self.race_canvas.pack(fill="both", expand=True)
        self.race_canvas.bind("<Configure>", lambda _e: self.draw_race_board())

    def _build_ranking_box(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="실시간 랭킹", padding=8)
        frame.pack(side="left", fill="both", expand=False)

        columns = ("rank", "team", "score", "missions", "set", "line")
        self.rank_tree = ttk.Treeview(frame, columns=columns, show="headings", height=14)
        self.rank_tree.heading("rank", text="#")
        self.rank_tree.heading("team", text="팀")
        self.rank_tree.heading("score", text="점수")
        self.rank_tree.heading("missions", text="활동수")
        self.rank_tree.heading("set", text="세트")
        self.rank_tree.heading("line", text="라인")

        self.rank_tree.column("rank", width=40, anchor="center")
        self.rank_tree.column("team", width=150)
        self.rank_tree.column("score", width=70, anchor="e")
        self.rank_tree.column("missions", width=70, anchor="center")
        self.rank_tree.column("set", width=70, anchor="center")
        self.rank_tree.column("line", width=70, anchor="center")
        self.rank_tree.pack(fill="both", expand=True)

    def _build_log_box(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="최근 로그", padding=8)
        frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.log_text = tk.Text(frame, height=12, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")

    def _build_manage_box(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="게임 관리", padding=8)
        frame.pack(side="left", fill="both", expand=False)

        ttk.Button(frame, text="새로고침", command=self.refresh_all).pack(fill="x", pady=(0, 8))
        ttk.Button(frame, text="게임 초기화", command=self.on_reset).pack(fill="x")

        info = (
            "점수 규칙:\n"
            "- 기본 10 + 난이도(10/20/30)\n"
            "- 3명 이상 1명당 +20\n"
            "- 카테고리 4종 완료 +40\n"
            "- 카테고리 3회마다 +25"
        )
        ttk.Label(frame, text=info, justify="left").pack(anchor="w", pady=(12, 0))

    def refresh_all(self) -> None:
        names = [t.name for t in self.game.teams]
        self.team_name_to_id = {t.name: t.id for t in self.game.teams}

        self.activity_team_combo["values"] = names
        if names:
            if self.activity_team_var.get() not in names:
                self.activity_team_var.set(names[0])
        else:
            self.activity_team_var.set("")

        self.refresh_ranking()
        self.refresh_logs()
        self.draw_race_board()

    def refresh_ranking(self) -> None:
        for iid in self.rank_tree.get_children():
            self.rank_tree.delete(iid)

        for idx, team in enumerate(self.game.sorted_teams(), start=1):
            line_count = sum(team.line_bonus_taken.values())
            set_done = "완료" if team.set_bonus_taken > 0 else "-"
            self.rank_tree.insert(
                "",
                "end",
                values=(idx, team.name, team.score, team.mission_count, set_done, line_count),
            )

    def refresh_logs(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        if not self.game.logs:
            self.log_text.insert("end", "로그가 없습니다.\n")
        else:
            for entry in self.game.logs[:120]:
                self.log_text.insert("end", f"[{entry.at}] {entry.text}\n")
        self.log_text.configure(state="disabled")

    def draw_race_board(self) -> None:
        c = self.race_canvas
        c.delete("all")

        teams = self.game.sorted_teams()
        if not teams:
            c.create_text(20, 20, anchor="nw", text="팀을 등록하면 레이스가 시작됩니다.", fill="#455")
            return

        top_score = max(t.score for t in teams)
        width = max(c.winfo_width(), 820)
        row_h = 56
        top_y = 30
        label_x = 20
        track_x1 = 190
        track_x2 = width - 60

        for idx, team in enumerate(teams, start=1):
            y = top_y + (idx - 1) * row_h
            c.create_text(label_x, y + 12, anchor="w", text=f"{idx}. {team.name}", font=("Helvetica", 10, "bold"))

            c.create_rectangle(track_x1, y, track_x2, y + 28, fill="#efdfc2", outline="#d7bf93", width=1)
            c.create_text(track_x2 + 16, y + 13, text="🏁", font=("Helvetica", 10))

            if top_score > 0:
                ratio = team.score / top_score
            else:
                ratio = 0
            ratio = min(max(ratio, 0.0), 1.0)
            token_x = track_x1 + ratio * (track_x2 - track_x1)
            token_x = min(max(token_x, track_x1 + 10), track_x2 - 10)

            c.create_oval(token_x - 14, y + 2, token_x + 14, y + 30, fill="#ca5d16", outline="#fff", width=2)
            c.create_text(token_x, y + 16, text=str(team.score), fill="white", font=("Helvetica", 9, "bold"))

    def on_add_team(self) -> None:
        ok, msg = self.game.add_team(self.team_name_var.get())
        if not ok:
            messagebox.showwarning("팀 등록", msg)
            return

        self.team_name_var.set("")
        self.refresh_all()

    def on_record_activity(self) -> None:
        team_name = self.activity_team_var.get().strip()
        team_id = self.team_name_to_id.get(team_name)
        if not team_id:
            messagebox.showwarning("활동 기록", "활동 팀을 선택해주세요.")
            return

        participant_raw = self.participant_var.get().strip()
        if not participant_raw.isdigit() or int(participant_raw) < 1:
            messagebox.showwarning("활동 기록", "참여 인원은 1 이상의 정수여야 합니다.")
            return

        difficulty_key = self.difficulty_label_to_key.get(self.difficulty_var.get().strip())
        category_key = self.category_label_to_key.get(self.category_var.get().strip())
        if not difficulty_key or not category_key:
            messagebox.showwarning("활동 기록", "난이도/카테고리를 다시 선택해주세요.")
            return

        ok, msg = self.game.record_activity(
            team_id=team_id,
            difficulty=difficulty_key,
            category=category_key,
            participant_count=int(participant_raw),
            title=self.activity_title_var.get(),
        )
        if not ok:
            messagebox.showwarning("활동 기록", msg)
            return

        self.activity_title_var.set("")
        self.refresh_all()

    def on_reset(self) -> None:
        confirm = messagebox.askyesno("게임 초기화", "모든 데이터를 초기화할까요?")
        if not confirm:
            return
        self.game.reset()
        self.refresh_all()


def main() -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    FriendlyScoreRaceGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
