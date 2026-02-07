# board_B_python

Python versions of Friendly Race `B` plan.

## 1) CLI version
```bash
cd board_B_python
python3 game.py
```

## 2) GUI version (Tkinter)
```bash
cd board_B_python
python3 gui.py
```

## GUI features
- Add team
- Record activity
  - base + difficulty + participant bonus (from 3 people)
  - throw chance +1 per 40 cumulative score
- Throw yut (Do/Gae/Geol/Yut/Mo/BackDo)
- 50-cell race track with koala checkpoints (10/20/30/40)
- Capture rule: return to latest 10-cell checkpoint
- Ranking, recent logs, reset

## Data storage
- State is saved automatically to `board_B_python/state.json`.
