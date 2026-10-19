"""Top-10 high score table, saved as JSON in the per-user data folder."""
import config

MAX_ENTRIES = 10

DEFAULT_TABLE = [
    {"name": "VEX", "score": 100000, "sector": 6, "lap": 1},
    {"name": "ARS", "score": 80000, "sector": 5, "lap": 1},
    {"name": "GAI", "score": 65000, "sector": 4, "lap": 1},
    {"name": "NOV", "score": 50000, "sector": 4, "lap": 1},
    {"name": "ACE", "score": 40000, "sector": 3, "lap": 1},
    {"name": "SOL", "score": 30000, "sector": 3, "lap": 1},
    {"name": "LUN", "score": 20000, "sector": 2, "lap": 1},
    {"name": "TER", "score": 15000, "sector": 2, "lap": 1},
    {"name": "ION", "score": 10000, "sector": 1, "lap": 1},
    {"name": "KID", "score": 5000, "sector": 1, "lap": 1},
]


def _valid(entry):
    return (isinstance(entry, dict)
            and isinstance(entry.get("name"), str)
            and isinstance(entry.get("score"), int)
            and isinstance(entry.get("sector"), int))


class HighScores:
    def __init__(self):
        self.entries = []
        self.load()

    def load(self):
        data = config.load_json(config.SCORES_FILE)
        entries = []
        if isinstance(data, list):
            for e in data:
                if _valid(e):
                    lap = e.get("lap", 1)
                    entries.append({
                        "name": "".join(c for c in e["name"].upper()[:3] if c.isalnum() or c in " .-!").ljust(3)[:3],
                        "score": max(0, min(9999999, e["score"])),
                        "sector": max(1, min(6, e["sector"])),
                        "lap": lap if isinstance(lap, int) and lap > 0 else 1,
                    })
        if not entries:
            entries = [dict(e) for e in DEFAULT_TABLE]
        entries.sort(key=lambda e: -e["score"])
        self.entries = entries[:MAX_ENTRIES]

    def save(self):
        config.save_json(config.SCORES_FILE, self.entries)

    def top_score(self):
        return self.entries[0]["score"] if self.entries else 0

    def qualifies(self, score):
        if score <= 0:
            return False
        if len(self.entries) < MAX_ENTRIES:
            return True
        return score > self.entries[-1]["score"]

    def insert(self, name, score, sector, lap):
        """Insert an entry; returns its rank index (or -1 if it fell off)."""
        entry = {"name": name[:3], "score": score, "sector": sector, "lap": lap}
        idx = len(self.entries)
        for i, e in enumerate(self.entries):
            if score > e["score"]:
                idx = i
                break
        self.entries.insert(idx, entry)
        del self.entries[MAX_ENTRIES:]
        self.save()
        return idx if idx < MAX_ENTRIES else -1
