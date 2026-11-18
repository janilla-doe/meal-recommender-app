"""Accounts, profiles, saved plans and daily check ins, in one small SQLite file.

Data minimisation: usernames (not emails), passwords stored only as salted PBKDF2 hashes,
income stored only as an income third (1, 2 or 3), never the actual pay.
Guest sessions never call these functions.
"""
import hashlib
import json
import os
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(os.environ.get("APP_DB", Path(__file__).parent / "data" / "users.db"))


def _conn():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init():
    with _conn() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                                          salt BLOB NOT NULL, pw_hash BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS profiles (user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                                             data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS plans (user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                                          made_on TEXT NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS checkins (user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                                             day TEXT NOT NULL, swap TEXT NOT NULL, done INTEGER NOT NULL,
                                             PRIMARY KEY (user_id, day, swap));
        CREATE TABLE IF NOT EXISTS shopping (id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                                             saved_on TEXT NOT NULL, days INTEGER NOT NULL, items TEXT NOT NULL,
                                             predicted REAL NOT NULL, actual REAL);
        CREATE TABLE IF NOT EXISTS spend (user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                                          day TEXT NOT NULL, amount REAL NOT NULL, PRIMARY KEY (user_id, day));
        """)


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)


def create_user(username, password):
    username = username.strip().lower()
    if len(username) < 3 or len(password) < 8:
        raise ValueError("Username needs 3+ characters and password 8+ characters.")
    salt = os.urandom(16)
    with _conn() as con:
        try:
            cur = con.execute("INSERT INTO users (username, salt, pw_hash) VALUES (?, ?, ?)",
                              (username, salt, _hash(password, salt)))
        except sqlite3.IntegrityError:
            raise ValueError("That username is taken.")
        return cur.lastrowid


def check_login(username, password):
    with _conn() as con:
        row = con.execute("SELECT id, salt, pw_hash FROM users WHERE username = ?",
                          (username.strip().lower(),)).fetchone()
    if row and _hash(password, row[1]) == row[2]:
        return row[0]
    return None


def save_profile(user_id, profile):
    allowed = {k: v for k, v in profile.items() if k not in ("take_home_pay", "pay_hint")}   # never store actual pay
    with _conn() as con:
        con.execute("INSERT INTO profiles (user_id, data) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET data = excluded.data",
                    (user_id, json.dumps(allowed)))


def get_profile(user_id):
    with _conn() as con:
        row = con.execute("SELECT data FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    return json.loads(row[0]) if row else None


def save_plan(user_id, plan):
    with _conn() as con:
        con.execute("INSERT INTO plans (user_id, made_on, data) VALUES (?, ?, ?) "
                    "ON CONFLICT(user_id) DO UPDATE SET made_on = excluded.made_on, data = excluded.data",
                    (user_id, date.today().isoformat(), json.dumps(plan)))


def get_plan(user_id):
    with _conn() as con:
        row = con.execute("SELECT made_on, data FROM plans WHERE user_id = ?", (user_id,)).fetchone()
    return (row[0], json.loads(row[1])) if row else (None, None)


def save_checkin(user_id, day, results, amount=None):
    with _conn() as con:
        for swap, done in results.items():
            con.execute("INSERT INTO checkins VALUES (?, ?, ?, ?) ON CONFLICT(user_id, day, swap) DO UPDATE SET done = excluded.done",
                        (user_id, day, swap, int(done)))
        if amount is not None:
            con.execute("INSERT INTO spend VALUES (?, ?, ?) ON CONFLICT(user_id, day) DO UPDATE SET amount = excluded.amount",
                        (user_id, day, float(amount)))


def history(user_id, days=14):
    with _conn() as con:
        c = con.execute("SELECT day, swap, done FROM checkins WHERE user_id = ? AND day >= date('now', ?) ORDER BY day",
                        (user_id, f"-{days} day")).fetchall()
        s = con.execute("SELECT day, amount FROM spend WHERE user_id = ? AND day >= date('now', ?) ORDER BY day",
                        (user_id, f"-{days} day")).fetchall()
    return c, s


def save_shopping(user_id, day, days, items, predicted, actual=None):
    with _conn() as con:
        con.execute("INSERT INTO shopping (user_id, saved_on, days, items, predicted, actual) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, day, int(days), json.dumps(items, default=str), float(predicted),
                     None if actual is None else float(actual)))


def get_shopping(user_id):
    """Saved shops, newest first: (date, days, number of items, predicted total, actual total)."""
    with _conn() as con:
        rows = con.execute("SELECT saved_on, days, items, predicted, actual FROM shopping WHERE user_id = ? ORDER BY id DESC",
                           (user_id,)).fetchall()
    return [(r[0], r[1], len(json.loads(r[2])), round(r[3], 2), None if r[4] is None else round(r[4], 2)) for r in rows]


def delete_user(user_id):
    with _conn() as con:
        con.execute("DELETE FROM users WHERE id = ?", (user_id,))
