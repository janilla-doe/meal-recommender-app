"""Run with:  pytest -q   (from the app folder)

Covers the model, the database and both user journeys. The guest journey test proves that
guest mode never creates or writes the database.
"""
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    path = tmp_path / "users.db"
    monkeypatch.setenv("APP_DB", str(path))
    import db
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


# ------------------------------------------------------------------ model
def test_plan_respects_budget_and_energy():
    from model import Model
    M = Model()
    xh = M.usual_day()
    r = M.plan(xh, "C", 4.0)
    assert r["cost"] <= 4.0 + 1e-3
    e0, e1 = xh @ M.KCAL, r["x"] @ M.KCAL
    assert 0.9 * e0 - 1 <= e1 <= 1.1 * e0 + 1


def test_vegetarian_and_dislikes_remove_groups():
    from model import Model, groups_for
    M = Model()
    xh = M.usual_day("Vegetarian", ["Fruit"])
    r = M.plan(xh, "C", 5.0, "Vegetarian", ["Fruit"])
    blocked = M.blocked("Vegetarian", ["Fruit"])
    assert np.all(r["x"][blocked] < 1e-4)
    assert any(M.groups.index(g) for g in groups_for("Fruit", M.G))


def test_no_target_is_broken_that_was_met():
    from model import Model
    M = Model()
    xh = M.usual_day()
    r = M.plan(xh, "C", 6.0)
    now, plan = M.targets_met(r["now"], r["drop_oily"]), M.targets_met(r["plan"], r["drop_oily"])
    if r["all_met"]:
        assert all(v for v in plan.values() if v is not None)


def test_meal_split_adds_up():
    from model import Model
    M = Model()
    r = M.plan(M.usual_day(), "C", 5.0)
    meals = M.split_into_meals(r["x"], 4, min_grams=0)
    assert len(meals) == 4
    total = sum(g for items in meals.values() for _, g in items)
    assert abs(total - 100 * r["x"].sum()) < 1.0


def test_income_tertile():
    from model import income_tertile
    assert income_tertile(1000, 1, 0) == 1
    assert income_tertile(3000, 1, 0) == 2
    assert income_tertile(9000, 2, 0) == 3


def test_allergen_filter():
    from model import Model
    M = Model()
    for g, items in M.PRODUCTS.items():
        for p in M.products_for(g, ["gluten"]):
            assert "gluten" not in p["allergens"]


# ------------------------------------------------------------------ database
def test_accounts_and_privacy(tmp_db):
    import db
    db.init()
    uid = db.create_user("tester", "password123")
    assert db.check_login("tester", "password123") == uid
    assert db.check_login("tester", "wrong-password") is None
    with pytest.raises(ValueError):
        db.create_user("tester", "password123")
    db.save_profile(uid, {"tertile": 1, "take_home_pay": 1500, "pay_hint": 1500})
    saved = db.get_profile(uid)
    assert "take_home_pay" not in saved and "pay_hint" not in saved, "actual pay must never be stored"
    raw = sqlite3.connect(tmp_db).execute("SELECT pw_hash FROM users").fetchone()[0]
    assert b"password123" not in raw
    db.save_checkin(uid, "2026-01-01", {"More fruit": True}, 3.5)
    db.save_shopping(uid, "2026-01-01", 7, [{"Item": "Bread", "Predicted £": 1.0, "Actual £": 1.2}], 1.0, 1.2)
    assert db.get_shopping(uid)[0][3:] == (1.0, 1.2)
    db.delete_user(uid)
    con = sqlite3.connect(tmp_db)
    assert con.execute("SELECT COUNT(*) FROM profiles").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM checkins").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM shopping").fetchone()[0] == 0


# ------------------------------------------------------------------ user journeys
def _through_survey(at):
    for _ in range(3):
        next_btn = [b for b in at.button if b.label == "Next"][0]
        next_btn.click().run()
    [b for b in at.button if b.label == "Make my plan"][0].click().run()
    return at


def test_guest_journey_saves_nothing(tmp_db):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=120).run()
    assert not at.exception
    # the welcome screen moves on by itself after a few seconds
    [b for b in at.button if b.label == "Continue as guest"][0].click().run()
    _through_survey(at)
    assert not at.exception
    assert any("Your meal plan" in t.value for t in at.title), "the first page after set up should be the meal plan"
    for page in ["✨ Discover", "🛒 Shopping", "📊 Progress", "💷 Money", "👤 Me", "🍽️ Today"]:
        at.radio[0].set_value(page).run()
        assert not at.exception, page
    # swipe through Discover: say no to the first card, yes to the rest, then update the plan
    at.radio[0].set_value("✨ Discover").run()
    first = True
    for _ in range(10):
        no = [b for b in at.button if b.label == "✖ Not for me"]
        yes = [b for b in at.button if b.label == "❤️ I'd try it"]
        if not yes:
            break
        (no[0] if first else yes[0]).click().run()
        first = False
        assert not at.exception
    upd = [b for b in at.button if b.label == "Update my plan"]
    if upd:
        upd[0].click().run()
        assert not at.exception
    assert not tmp_db.exists(), "guest mode must never create the database"


def test_account_journey(tmp_db):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP_DIR / "app.py"), default_timeout=120).run()
    ti = {t.label: t for t in at.text_input}
    ti["Choose a username"].input("jane_test")
    ti["Choose a password (8+ characters)"].input("password123")
    ti["Repeat password"].input("password123")
    [b for b in at.button if b.label == "Create account"][0].click().run()
    assert not at.exception
    _through_survey(at)
    assert not at.exception and tmp_db.exists()
    at.radio[0].set_value("📊 Progress").run()
    assert not at.exception
    [b for b in at.button if b.label == "Save today"][0].click().run()
    assert not at.exception
    import db
    made_on, saved = db.get_plan(1)
    assert saved is not None and made_on is not None, "an account's plan should be saved"
    at.radio[0].set_value("🛒 Shopping").run()
    assert not at.exception
    [b for b in at.button if b.label == "💾 Save this shop"][0].click().run()
    assert not at.exception
    assert len(db.get_shopping(1)) == 1, "a saved shop should be stored for an account"
    at.radio[0].set_value("👤 Me").run()
    [b for b in at.button if b.label == "Delete everything"][0].click().run()
    assert sqlite3.connect(tmp_db).execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0


def test_daily_plans_vary_but_keep_budget():
    from model import Model
    M = Model()
    xh = M.usual_day()
    days = [M.plan(xh, "C", 4.5, day_seed=740000 + d) for d in range(3)]
    for r in days:
        assert r["cost"] <= 4.5 + 1e-3
    assert not np.allclose(days[0]["x"], days[1]["x"], atol=1e-3), "different days should give different plans"
    again = M.plan(xh, "C", 4.5, day_seed=740000)
    assert np.allclose(days[0]["x"], again["x"], atol=1e-4), "the same day should always give the same plan"
