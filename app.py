"""Research prototype: healthy, affordable food plans close to what you already eat.

Flow: green welcome screen -> log in / sign up / guest -> 4 step set up -> plan, meals, costs, tracking, profile.
Guest mode saves nothing. Accounts store only what the person enters, in a local SQLite file.
"""
from datetime import date, timedelta
from html import escape

import pandas as pd
import streamlit as st

import db
from model import (DIETS, FOOD_CHOICES, INCOME_TERTILE_CUTS, OCCASION_ORDER, PLAIN, TARGETS, UK_ALLERGENS, Model,
                   amount_text, friendly, income_tertile)

st.set_page_config(page_title="Welcome", page_icon="🥕", layout="centered", initial_sidebar_state="collapsed")

M = Model()
SC_LABEL = M.S["scenario_labels"]
BANDS = ["Lower", "Middle", "Higher"]
MEAL_ICON = {"Early snack": "🌅", "Breakfast": "🍳", "Morning snack": "☕", "Lunch": "🥪",
             "Afternoon snack": "🍎", "Evening meal": "🍲", "Late snack": "🌙"}
ss = st.session_state
for k, v in {"page": "welcome", "user_id": None, "guest": False, "profile": None, "plan": None, "step": 1}.items():
    ss.setdefault(k, v)

# ----------------------------------------------------------------------- styling
BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, label {font-family: 'Nunito', system-ui, sans-serif !important;}
#MainMenu, footer, header [data-testid="stToolbar"], [data-testid="stDecoration"] {visibility: hidden;}
header[data-testid="stHeader"] {display: none !important;}
.block-container {max-width: 680px; padding-top: 2.5rem !important; padding-bottom: 3rem;}
h1, h2, h3 {color: #1B5E20; font-weight: 800 !important; letter-spacing: -.01em;}
.stButton > button, .stFormSubmitButton > button {border-radius: 999px !important; padding: .65rem 1rem !important; font-weight: 700 !important;}
div[data-baseweb="input"], div[data-baseweb="select"] > div {border-radius: 12px !important;}
.card {background: #fff; border: 1px solid #E3ECE3; border-radius: 18px; padding: 1rem 1.15rem; margin: .55rem 0;
       box-shadow: 0 2px 10px rgba(27, 94, 32, .06);}
.hero {background: linear-gradient(135deg, #2E7D32, #66BB6A); color: #fff; border-radius: 22px; padding: 1.3rem 1.4rem; margin: .4rem 0 1rem;}
.hero .big {font-size: 2.3rem; font-weight: 800; line-height: 1.1;}
.hero .small {opacity: .92; font-size: 1rem;}
.pill {display: inline-block; padding: .35rem .75rem; border-radius: 999px; margin: .2rem .25rem .2rem 0; font-size: .92rem; font-weight: 600;}
.pill.ok {background: #E8F5E9; color: #1B5E20;} .pill.no {background: #F3F3F3; color: #888;}
.item {display: flex; gap: .7rem; align-items: center; padding: .45rem 0; border-bottom: 1px dashed #EDF2ED;}
.item:last-child {border-bottom: none;} .item .ic {font-size: 1.5rem; width: 2rem; text-align: center;}
.item .nm {font-weight: 700;} .item .am {color: #5f6b5f; font-size: .92rem;}
.tag {font-size: .8rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; margin-bottom: .3rem;}
.more .tag {color: #2E7D32;} .less .tag {color: #E65100;}
.muted {color: #6b756b; font-size: .92rem;}
.stepper {display: flex; gap: .4rem; margin: .2rem 0 1rem;} .stepper div {flex: 1; height: 7px; border-radius: 99px; background: #E3ECE3;}
.stepper div.on {background: #43A047;}
.bars .row {margin: .5rem 0;} .bars .lbl {display: flex; justify-content: space-between; font-size: .92rem; font-weight: 600;}
.bars .track {position: relative; height: 10px; background: #EEF3EE; border-radius: 99px; margin-top: .25rem;}
.bars .fill {position: absolute; left: 0; top: 0; bottom: 0; border-radius: 99px;}
.bars .goal {position: absolute; top: -3px; bottom: -3px; width: 2px; background: #1B1B1B; opacity: .55;}
.kpis {display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem;}
.kpi {background: #F4FAF3; border-radius: 16px; padding: .7rem .8rem; text-align: center;}
.kpi .v {font-size: 1.45rem; font-weight: 800; color: #1B5E20;} .kpi .l {font-size: .8rem; color: #5f6b5f;}
.date {font-size: .95rem; font-weight: 700; color: #43A047; text-transform: uppercase; letter-spacing: .05em;}
.aisle {font-weight: 800; color: #1B5E20; margin: .2rem 0 .1rem;}
.swipe-card {border-radius: 26px; overflow: hidden; background: #fff; box-shadow: 0 10px 30px rgba(27,94,32,.18);
              margin: .4rem 0 1rem; transition: transform .25s ease, opacity .25s ease; touch-action: pan-y; user-select: none;}
.swipe-card .photo {height: 260px; display: flex; align-items: center; justify-content: center; font-size: 6rem;
                    background: linear-gradient(135deg, #E8F5E9, #C8E6C9); position: relative;}
.swipe-card .photo img {position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; background: #fff;}
.swipe-card .photo .cap {position: absolute; left: .7rem; bottom: .7rem; background: rgba(0,0,0,.62); color: #fff;
                         font-size: .78rem; font-weight: 700; border-radius: 999px; padding: .25rem .65rem; z-index: 2;}
.swipe-card .body {padding: 1rem 1.2rem 1.2rem;}
.st-key-swipe_no_side button, .st-key-swipe_yes_side button {width: 3.6rem; height: 3.6rem; border-radius: 50% !important;
    padding: 0 !important; font-size: 1.5rem !important; box-shadow: 0 4px 14px rgba(0,0,0,.12);}
.st-key-swipe_no_side button {background: #fff !important; color: #C62828 !important; border: 1px solid #E0E0E0 !important;}
.st-key-swipe_yes_side button {background: #2E7D32 !important; color: #fff !important; border: none !important;}
.st-key-swipe_no_side, .st-key-swipe_yes_side {display: flex; justify-content: center;}
@media (max-width: 640px) {.st-key-swipe_no_side, .st-key-swipe_yes_side {display: none !important;}}
.swipe-card .title {font-size: 1.5rem; font-weight: 800; color: #1B1B1B;}
.swipe-card .chips span {display: inline-block; background: #E8F5E9; color: #1B5E20; border-radius: 999px; padding: .25rem .65rem;
                         margin: .25rem .3rem 0 0; font-size: .85rem; font-weight: 700;}
.swipe-count {text-align: center; color: #6b756b; font-size: .9rem;}
.idea {background: #FFF8E1; border-radius: 12px; padding: .45rem .7rem; margin-top: .5rem; font-size: .92rem;}
.faq b {color: #1B5E20;}
div[role="radiogroup"] {gap: .35rem; flex-wrap: wrap;}
div[role="radiogroup"] label {background: #F1F8E9; border-radius: 999px; padding: .35rem .85rem !important; margin: 0 !important;}
div[role="radiogroup"] label:has(input:checked) {background: #2E7D32;} div[role="radiogroup"] label:has(input:checked) p {color: #fff !important;}
label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) {display: none !important;}
</style>
"""
SPLASH_CSS = """
<style>
.stApp {background: linear-gradient(160deg, #1B5E20 0%, #2E7D32 45%, #66BB6A 100%) !important;}
.block-container {padding-top: 2rem;}
@keyframes rise {0% {opacity: 0; transform: translateY(26px);} 100% {opacity: 1; transform: none;}}
@keyframes bob {0%, 100% {transform: translateY(0) rotate(0);} 50% {transform: translateY(-12px) rotate(-6deg);}}
@keyframes spin {to {transform: rotate(360deg);}}
@keyframes fill {0% {width: 0;} 100% {width: 100%;}}
.splash {text-align: center; color: #fff; padding: 3rem 0 1rem;}
.splash .food span {display: inline-block; font-size: 2.6rem; margin: 0 .3rem; animation: bob 2.6s ease-in-out infinite;}
.splash .food span:nth-child(2) {animation-delay: .2s;} .splash .food span:nth-child(3) {animation-delay: .4s;}
.splash .food span:nth-child(4) {animation-delay: .6s;} .splash .food span:nth-child(5) {animation-delay: .8s;}
.splash h1 {color: #fff !important; font-size: 3.6rem; margin: .8rem 0 .2rem; animation: rise 1s ease-out both;}
.splash p {font-size: 1.15rem; opacity: .95; animation: rise 1s .3s ease-out both; max-width: 30rem; margin: 0 auto;}
.bar {height: 6px; background: rgba(255,255,255,.25); border-radius: 99px; max-width: 220px; margin: 2.2rem auto 2rem; overflow: hidden;}
.bar div {height: 100%; background: #fff; animation: fill 2.8s ease-out both;}
.note {color: #fff; background: rgba(255,255,255,.14); border-radius: 16px; padding: .9rem 1rem; font-size: .95rem;
       animation: rise 1s .8s ease-out both;}
</style>
"""
st.markdown(BASE_CSS, unsafe_allow_html=True)


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def go(page):
    ss.page = page
    st.rerun()


def is_account():
    return ss.user_id is not None and not ss.guest


def half(x, cap):
    return min(round(float(x) * 2) / 2, cap)


def avg_portions(group, grams, fallback):
    return M.AVG[M.groups.index(group)] * 100 / grams if group in M.groups else fallback


def default_profile():
    return {"age": 30, "adults": 1, "children": 0, "income_known": False, "tertile": 1,
            "weekly_spend": None, "scenario": "C", "diet": "No restrictions", "allergens": [], "dislikes": [],
            "loves": [], "meals_per_day": 3,
            "sliders": {"fruit": half(avg_portions("Fresh and frozen fruits", 80, 1), 6),
                        "veg": half(avg_portions("Other vegetables", 80, 1), 6),
                        "white_bread": half(avg_portions("Wheat bread, white", 36, 2), 8),
                        "brown_bread": half(avg_portions("Wheat bread, wholemeal", 36, 0.5), 8),
                        "fizzy": half(avg_portions("Soft drinks, with added sugar, carbonated", 330, 0.5), 4),
                        "sweet": 2.0}}


def budget_of(p):
    return p["weekly_spend"] / 7 if p.get("weekly_spend") else M.budget_for(p["scenario"], p["tertile"])


def make_plan(p):
    ss.day_plans = {}
    xh = M.usual_day(p["diet"], p["dislikes"], p["sliders"])
    for gname in p.get("excluded_groups", []):
        if gname in M.groups:
            xh[M.groups.index(gname)] = 0
    res = M.plan(xh, p["scenario"], budget_of(p), p["diet"], p["dislikes"], p["loves"], p["age"],
                 p.get("liked_groups", []), p.get("excluded_groups", []))
    more, less = M.swaps(xh, res["x"])
    res.update({"xh": xh, "more": more, "less": less})
    if is_account():
        db.save_plan(ss.user_id, {"x": res["x"].tolist(), "more": more.round(0).to_dict(),
                                  "less": less.round(0).to_dict(), "cost": res["cost"], "budget": res["budget"]})
    return res


def two_buttons(left, right):
    c1, c2 = st.columns(2)
    return c1.form_submit_button(left, width="stretch"), c2.form_submit_button(right, type="primary", width="stretch")


def items_card(title_cls, tag, series):
    rows = "".join(f'<div class="item"><div class="ic">{M.icon(g)}</div><div><div class="nm">{escape(friendly(g))}</div>'
                   f'<div class="am">{escape(amount_text(g, v))} a day</div></div></div>' for g, v in series.items())
    html(f'<div class="card {title_cls}"><div class="tag">{tag}</div>{rows or "<div class=muted>No big changes needed.</div>"}</div>')


# ======================================================================= welcome (green splash, moves on by itself)
if ss.page == "welcome":
    html(SPLASH_CSS)
    html('<div class="splash"><div class="food"><span>🥕</span><span>🍎</span><span>🥦</span><span>🍞</span><span>🐟</span></div>'
         '<h1>Welcome</h1><p>Healthier food that fits your budget, built around what you already like to eat.</p>'
         '<div class="bar"><div></div></div></div>')
    html('<div class="note">🔬 A university research prototype. Not medical or dietetic advice, and '
         '<b>not for use in pregnancy, while breastfeeding</b> or with a medical diet.</div>')
    import time
    time.sleep(3)
    go("auth")

# ======================================================================= log in
if ss.page == "auth":
    st.title("Hello 👋")
    st.caption("Make an account to save your plan and track your progress, or try it as a guest.")
    t_guest, t_login, t_signup = st.tabs(["Try as a guest", "Log in", "Create account"])
    with t_guest:
        html('<div class="card">✨ Try everything without an account.<br><span class="muted">Nothing you enter is saved, '
             'and it is cleared when you close the page.</span></div>')
        if st.button("Continue as guest", type="primary", width="stretch"):
            ss.user_id, ss.guest, ss.profile, ss.plan, ss.step = None, True, None, None, 1
            go("survey")
    with t_login:
        with st.form("login"):
            u = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", type="primary", width="stretch"):
                db.init()
                uid = db.check_login(u, pw)
                if uid:
                    ss.user_id, ss.guest = uid, False
                    ss.profile, ss.plan = db.get_profile(uid), None
                    go("home" if ss.profile else "survey")
                st.error("Username or password not recognised.")
    with t_signup:
        with st.form("signup"):
            u = st.text_input("Choose a username")
            pw = st.text_input("Choose a password (8+ characters)", type="password")
            pw2 = st.text_input("Repeat password", type="password")
            st.caption("🔒 Use a username, not your email. Your pay is never stored, only your income band. "
                       "You can delete your account at any time.")
            if st.form_submit_button("Create account", type="primary", width="stretch"):
                if pw != pw2:
                    st.error("Passwords do not match.")
                else:
                    try:
                        db.init()
                        ss.user_id, ss.guest = db.create_user(u, pw), False
                        ss.profile, ss.plan, ss.step = None, None, 1
                        go("survey")
                    except ValueError as e:
                        st.error(str(e))
    st.stop()

# ======================================================================= set up (4 steps)
if ss.page == "survey":
    p = ss.profile or default_profile()
    p["scenario"] = "C"      # always the latest prices
    if isinstance(p.get("age"), str):            # profiles saved by an older version
        p["age"] = 30 if p["age"] == "19 to 50" else 55
    titles = ["About you", "Your money", "Your food", "A usual day"]
    html('<div class="stepper">' + "".join(f'<div class="{"on" if i < ss.step else ""}"></div>' for i in range(4)) + "</div>")
    st.caption(f"Step {ss.step} of 4")
    st.title(titles[ss.step - 1])

    if ss.step == 1:
        with st.form("s1"):
            p["age"] = int(st.number_input("How old are you?", min_value=16, max_value=100, value=int(p["age"]), step=1))
            c1, c2 = st.columns(2)
            p["adults"] = int(c1.number_input("Adults at home (including you)", 1, 8, int(p["adults"])))
            p["children"] = int(c2.number_input("Children under 14", 0, 8, int(p["children"])))
            p["meals_per_day"] = st.slider("How many times do you usually eat a day, including snacks?", 2, 6, int(p["meals_per_day"]))
            if st.form_submit_button("Next", type="primary", width="stretch"):
                if not 19 <= p["age"] <= 64:
                    st.error("Sorry, this prototype is designed for women aged 19 to 64, the group the model was built from.")
                else:
                    ss.profile, ss.step = p, 2
                    st.rerun()

    elif ss.step == 2:
        st.caption("🔒 Pay is only used to estimate a typical food budget. It is never saved, only your income band is.")
        known = st.radio("Household take home pay (after tax)", ["Enter it", "Prefer not to say"],
                         index=0 if p["income_known"] else 1, horizontal=True)
        scale = 1 + 0.5 * max(p["adults"] - 1, 0) + 0.3 * p["children"]
        lo, hi = INCOME_TERTILE_CUTS
        if known == "Enter it":
            pay = st.number_input("Take home pay per month, whole household (£)", 0, 20000, int(p.get("pay_hint", 1600)), step=50)
            tertile = income_tertile(pay, p["adults"], p["children"])
            p["pay_hint"] = pay      # kept only for this session; never saved to the database
        else:
            band = st.select_slider("Your household income is", BANDS, value=BANDS[p["tertile"] - 1])
            tertile = BANDS.index(band) + 1
        typical = M.budget_for(p["scenario"], tertile)
        html(f'<div class="card">💷 <b>{BANDS[tertile - 1]} income band</b> → typical food spend <b>£{typical:.2f} a day</b> '
             f'(£{7 * typical:.0f} a week) per person.<br><span class="muted">For a household like yours, the bands are: lower under '
             f'£{lo * scale / 12:,.0f} a month, middle £{lo * scale / 12:,.0f} to £{hi * scale / 12:,.0f}, higher over £{hi * scale / 12:,.0f}. '
             f'Typical spend: £{M.budget_for(p["scenario"], 1):.2f}, £{M.budget_for(p["scenario"], 2):.2f} and '
             f'£{M.budget_for(p["scenario"], 3):.2f} a day (Defra Family Food).</span></div>')
        own = st.toggle("I'd rather use my own weekly food budget", value=bool(p["weekly_spend"]),
                        help="Use this if you spend more or less than is typical, or want to spend less.")
        spend = st.number_input("Food budget per person per week (£)", 7, 150, int(p["weekly_spend"] or round(7 * typical)), step=1) if own else None
        c1, c2 = st.columns(2)
        back = c1.button("Back", width="stretch")
        nxt = c2.button("Next", type="primary", width="stretch")
        if back or nxt:
            p["income_known"] = known == "Enter it"
            p["tertile"] = tertile
            p["weekly_spend"] = float(spend) if own else None
            ss.profile, ss.step = p, (1 if back else 3)
            st.rerun()

    elif ss.step == 3:
        with st.form("s3"):
            p["diet"] = st.selectbox("Your diet", DIETS, index=DIETS.index(p["diet"]))
            choices = list(FOOD_CHOICES)
            p["loves"] = st.multiselect("❤️ Foods you love (we'll keep these close to what you eat now)", choices, default=p["loves"])
            p["dislikes"] = st.multiselect("🚫 Foods you don't eat or don't like (we'll leave these out)", choices, default=p["dislikes"])
            p["allergens"] = st.multiselect("⚠️ Allergies (to filter product suggestions)", UK_ALLERGENS,
                                            default=p["allergens"], format_func=lambda a: a.replace("-", " ").capitalize())
            back, nxt = two_buttons("Back", "Next")
            if back or nxt:
                clash = set(p["loves"]) & set(p["dislikes"])
                if clash and nxt:
                    st.error("These are in both lists: " + ", ".join(sorted(clash)))
                else:
                    ss.profile, ss.step = p, (2 if back else 4)
                    st.rerun()

    elif ss.step == 4:
        with st.form("s4"):
            st.caption("Roughly is fine. A portion of fruit or veg is about a handful.")
            s = p["sliders"]
            s["fruit"] = st.slider("🍎 Portions of fruit", 0.0, 6.0, half(s["fruit"], 6), 0.5, format="%.1f")
            s["veg"] = st.slider("🥦 Portions of vegetables", 0.0, 6.0, half(s["veg"], 6), 0.5, format="%.1f")
            s["white_bread"] = st.slider("🍞 Slices of white bread", 0.0, 8.0, half(s["white_bread"], 8), 0.5, format="%.1f")
            s["brown_bread"] = st.slider("🌾 Slices of wholemeal bread", 0.0, 8.0, half(s["brown_bread"], 8), 0.5, format="%.1f")
            s["fizzy"] = st.slider("🥤 Cans of sugary fizzy drink", 0.0, 4.0, half(s["fizzy"], 4), 0.5, format="%.1f")
            s["sweet"] = st.slider("🍪 Biscuits, cakes or chocolate (about 30 g each)", 0.0, 8.0, half(s["sweet"], 8), 0.5, format="%.1f")
            back, done = two_buttons("Back", "Make my plan")
            if back:
                ss.profile, ss.step = p, 3
                st.rerun()
            if done:
                ss.profile = p
                if is_account():
                    db.save_profile(ss.user_id, p)
                with st.spinner("Working out your plan..."):
                    ss.plan = make_plan(p)
                go("home")
    st.stop()

# ======================================================================= main app
import streamlit.components.v1 as components

p = ss.profile or default_profile()
p["scenario"] = "C"          # always the latest prices
p.setdefault("liked_groups", [])
p.setdefault("excluded_groups", [])
if isinstance(p.get("age"), str):
    p["age"] = 30 if p["age"] == "19 to 50" else 55
if ss.plan is None:
    with st.spinner("Working out your plan..."):
        ss.plan = make_plan(p)
R = ss.plan
now_t, plan_t = M.targets_met(R["now"], R["drop_oily"]), M.targets_met(R["plan"], R["drop_oily"])
SHOWN_T = [t for t in TARGETS if now_t[t] is not None]
N_NOW, N_PLAN = sum(bool(now_t[t]) for t in SHOWN_T), sum(bool(plan_t[t]) for t in SHOWN_T)
BUDGET_WHY = ("This is what households on a similar income in the UK typically spend on food for each person, "
              "from the government's Family Food survey.") if not p.get("weekly_spend") else "This is the weekly food spend you told us, divided by 7."

AISLE = {"Fruit": "🥬 Fruit and veg", "Vegetables": "🥬 Fruit and veg", "Potatoes": "🥬 Fruit and veg",
         "Bread": "🍞 Bakery", "Sandwiches": "🍞 Bakery", "Dairy": "🧀 Dairy and eggs", "Eggs": "🧀 Dairy and eggs",
         "Red and processed meat": "🥩 Meat and fish", "Poultry": "🥩 Meat and fish", "Fish": "🥩 Meat and fish",
         "Pies, burgers and sausages": "🥩 Meat and fish", "Breakfast cereals": "🥫 Cupboard", "Rice, pasta and grains": "🥫 Cupboard",
         "Nuts, seeds and meat alternatives": "🥫 Cupboard", "Fats, sauces and condiments": "🥫 Cupboard", "Pizza": "❄️ Frozen and chilled",
         "Sweet foods": "🍪 Snacks and drinks", "Savoury snacks": "🍪 Snacks and drinks", "Drinks": "🍪 Snacks and drinks"}
TIPS = {
    "Fibre 30 g": ["Swap white bread for wholemeal: same price, double the fibre.", "Add a tin of beans or lentils to stews, curries and soups.",
                   "Keep the skins on potatoes; that's where much of the fibre is.", "Porridge oats are one of the cheapest sources of fibre."],
    "Free sugars under 5%": ["Try sugar free squash or water in place of fizzy drinks.", "Swap one sweet snack for a piece of fruit each day."],
    "Saturated fat under 11%": ["Grill rather than fry, and trim visible fat from meat.", "Semi skimmed milk has about half the saturated fat of whole milk."],
    "Salt under 6 g": ["Taste before adding salt; herbs, pepper and lemon add flavour.", "Choose tinned veg and beans 'in water' rather than salted."],
    "5 a day": ["Frozen and tinned fruit and veg count, and they're often cheaper.", "A handful of frozen veg in pasta or rice is a quick extra portion."],
    "Red meat under 70 g": ["Make mince go further by mixing in lentils or beans."],
    "Oily fish 140 g a week": ["Tinned sardines and mackerel are cheap oily fish; one tin a week gets you close.",
                               "Mackerel pâté on toast is a quick, cheap oily fish lunch."],
}
# simple meal ideas: if both kinds of food are in a meal, suggest the dish
IDEAS = [({"Potatoes"}, {"Vegetables"}, "Jacket potato with beans or veg"),
         ({"Breakfast cereals"}, {"Fruit"}, "Porridge or cereal topped with fruit"),
         ({"Bread"}, {"Eggs"}, "Eggs on wholemeal toast"),
         ({"Bread"}, {"Fish"}, "Sardines or mackerel on toast"),
         ({"Rice, pasta and grains"}, {"Vegetables"}, "Pasta or rice with a tomato and veg sauce"),
         ({"Poultry"}, {"Vegetables"}, "Chicken and veg traybake"),
         ({"Vegetables"}, {"Bread"}, "Soup with a wholemeal roll"),
         ({"Potatoes"}, {"Fish"}, "Fish with potatoes and peas"),
         ({"Bread"}, {"Dairy"}, "Cheese and salad sandwich on wholemeal")]


def plain(t):
    return PLAIN[t][0]


def tip_for_today():
    pool = [t for b in (R["binding"] or SHOWN_T) for t in TIPS.get(b, [])] or [t for v in TIPS.values() for t in v]
    return pool[date.today().toordinal() % len(pool)]


def meal_idea(items, day=None):
    comps = {M.G.loc[g, "component"] for g, _ in items if g in M.G.index}
    matches = [idea for a, b, idea in IDEAS if comps & a and comps & b]
    if not matches:
        return None
    return matches[(day.toordinal() if day else 0) % len(matches)]


def day_plan(d):
    """The plan for a given date: the same preferences and goals, nudged so each day is a little different."""
    ss.setdefault("day_plans", {})
    key = d.isoformat()
    if key not in ss.day_plans:
        xh = R["xh"]
        r = M.plan(xh, p["scenario"], budget_of(p), p["diet"], p["dislikes"], p["loves"], p["age"],
                   p.get("liked_groups", []), p.get("excluded_groups", []), day_seed=d.toordinal())
        ss.day_plans[key] = r
    return ss.day_plans[key]


def shopping_list(days=7):
    price = M.price(p["scenario"])
    total = sum(day_plan(date.today() + timedelta(days=k))["x"] for k in range(days))
    rows = []
    for j, gname in enumerate(M.groups):
        grams = 100 * total[j]
        if grams < 50 or gname in ("Other: Tea, coffee and water", "Other foods"):
            continue
        comp = M.G.loc[gname, "component"]
        rows.append({"aisle": AISLE.get(comp, "🥫 Cupboard"), "icon": M.icon(gname), "item": friendly(gname),
                     "amount": amount_text(gname, grams), "grams": grams, "cost": grams / 100 * price[j]})
    return pd.DataFrame(rows).sort_values(["aisle", "cost"], ascending=[True, False]) if rows else pd.DataFrame()


def bar(label, now_v, plan_v, goal, unit, higher_is_better, cap):
    pos = lambda v: max(0, min(100, 100 * v / cap))
    good = (plan_v >= goal) if higher_is_better else (plan_v <= goal)
    colour = "#43A047" if good else "#FFA000"
    return (f'<div class="row"><div class="lbl"><span>{label}</span><span>{now_v:.1f} → <b>{plan_v:.1f}</b> {unit}</span></div>'
            f'<div class="track"><div class="fill" style="width:{pos(now_v)}%;background:#CFD8CF"></div>'
            f'<div class="fill" style="width:{pos(plan_v)}%;background:{colour};opacity:.85"></div>'
            f'<div class="goal" style="left:{pos(goal)}%"></div></div></div>')


def save_profile_and_replan():
    ss.profile = p
    if is_account():
        db.save_profile(ss.user_id, p)
    ss.plan = make_plan(p)


def goal_pills(status):
    return "".join(f'<span class="pill {"ok" if status[t] else "no"}" title="{escape(PLAIN[t][1])}">'
                   f'{"✅" if status[t] else "◻️"} {plain(t)}</span>' for t in SHOWN_T)


PAGES = ["🍽️ Today", "✨ Discover", "🛒 Shopping", "📊 Progress", "💷 Money", "👤 Me"]
nav = st.radio("Menu", PAGES, horizontal=True, label_visibility="collapsed")
if ss.guest:
    st.caption("👤 Guest mode: nothing is saved.")

# ----------------------------------------------------------------------- today (first page)
if nav == PAGES[0]:
    week = [date.today() + timedelta(days=k) for k in range(7)]
    labels = ["Today" if d == date.today() else f"{d:%a %d}" for d in week]
    pick = st.radio("Day", labels, horizontal=True, label_visibility="collapsed", key="daypick")
    day = week[labels.index(pick)]
    with st.expander("📅 Pick another date"):
        other = st.date_input("Date", value=day, min_value=date.today() - timedelta(days=30),
                              max_value=date.today() + timedelta(days=60), format="DD/MM/YYYY")
        if other != day:
            day = other
    D = day_plan(day)
    html(f'<div class="date">{day:%A %d %B %Y}</div>')
    st.title("Your meal plan")
    diff = D["usual_cost"] - D["cost"]
    saving = f"£{diff:.2f} less than your usual day" if diff >= 0.01 else (f"£{-diff:.2f} more than your usual day" if diff <= -0.01 else "about the same as your usual day")
    d_t = M.targets_met(D["plan"], D["drop_oily"])
    n_d = sum(bool(d_t[t]) for t in SHOWN_T)
    html(f'<div class="hero"><div class="small">This day\'s food costs about</div><div class="big">£{D["cost"]:.2f}</div>'
         f'<div class="small">{saving} · your budget is £{D["budget"]:.2f} a day</div></div>')
    prev = day_plan(day - timedelta(days=1))
    new_today = [g for j, g in enumerate(M.groups) if D["x"][j] * 100 >= 30 and prev["x"][j] * 100 < 15
                 and g not in ("Other: Tea, coffee and water", "Other foods")]
    if new_today:
        html('<div class="card">🔄 <b>New compared with the day before:</b> '
             + ", ".join(f"{M.icon(g)} {escape(friendly(g).lower())}" for g in new_today[:4])
             + '<br><span class="muted">Every day changes a little, but always fits your likes, your budget and the healthy goals.</span></div>')
    with st.expander(f"Why £{D['budget']:.2f}?"):
        st.write(f"**£{D['budget']:.2f} a day (£{7 * D['budget']:.2f} a week) is your food budget.** {BUDGET_WHY}")
        st.write("Your plan uses this budget to give you the healthiest day closest to what you like. If you'd rather spend "
                 "less, go to **💷 Money** to see a cheaper healthy day, or change your budget in **👤 Me**.")
    html(f'<div class="card"><div class="tag" style="color:#1B5E20">Healthy eating goals: {n_d} of {len(SHOWN_T)} met</div>'
         + goal_pills(d_t) + '</div>')
    meals = M.split_into_meals(D["x"], p["meals_per_day"], min_grams=20)
    lines = [f"Meal plan for {day:%A %d %B %Y}", ""]
    for occ in [o for o in OCCASION_ORDER if o in meals]:
        items = meals[occ][:6]
        rows = "".join(f'<div class="item"><div class="ic">{M.icon(g)}</div><div><div class="nm">{escape(friendly(g))}</div>'
                       f'<div class="am">{escape(amount_text(g, grams))}</div></div></div>' for g, grams in items)
        idea = meal_idea(items, day)
        idea_html = f'<div class="idea">🍳 <b>Idea:</b> {escape(idea)}</div>' if idea else ""
        html(f'<div class="card"><div class="tag" style="color:#1B5E20">{MEAL_ICON.get(occ, "🍽️")} {occ}</div>'
             f'{rows or "<div class=muted>A drink or a light snack</div>"}{idea_html}</div>')
        lines += [occ.upper()] + [f"  - {friendly(g)}: {amount_text(g, grams)}" for g, grams in items] + ([f"  Idea: {idea}"] if idea else []) + [""]
    if not D["all_met"]:
        st.warning("The budget can't quite cover every goal on this day, so the plan gets as close as it can. See **💷 Money**.")
    tips = [t for b in (D["binding"] or SHOWN_T) for t in TIPS.get(b, [])] or [t for v in TIPS.values() for t in v]
    html(f'<div class="card">💡 <b>Tip of the day:</b> {escape(tips[day.toordinal() % len(tips)])}</div>')
    st.download_button("⬇️ Save this plan to my phone", "\n".join(lines), file_name=f"meal_plan_{day:%Y-%m-%d}.txt", width="stretch")
    with st.expander("🗓️ Download the whole week"):
        wk = []
        for d_ in week:
            m_ = M.split_into_meals(day_plan(d_)["x"], p["meals_per_day"], min_grams=20)
            wk += [f"=== {d_:%A %d %B} ==="] + [f"{o}: " + ", ".join(f"{friendly(g)} ({amount_text(g, gr)})" for g, gr in m_[o][:6])
                                               for o in OCCASION_ORDER if o in m_] + [""]
        st.download_button("⬇️ Download 7 day plan", "\n".join(wk), file_name=f"week_plan_{date.today():%Y-%m-%d}.txt", width="stretch")

# ----------------------------------------------------------------------- discover (swipe cards)
elif nav == PAGES[1]:
    st.title("Discover")
    st.caption("Here are foods your plan suggests. Swipe right (or tap ❤️) if you'd try it, left (or tap ✖) if not. "
               "We'll update your plan to match.")
    def photos(g):
        return [pr["image"] for pr in M.products_for(g, p["allergens"]) if pr.get("image")]
    pool = [g for g in R["more"].index if g not in p["excluded_groups"]]
    with_photo = [g for g in pool if photos(g)]
    cands = (with_photo or pool)[:8]          # foods without any product photo are left out of swiping
    ss.setdefault("swipe", {"i": 0, "yes": [], "no": [], "for": None})
    sw = ss.swipe
    if sw["for"] != tuple(cands):
        sw.update({"i": 0, "yes": [], "no": [], "for": tuple(cands)})
    if not cands:
        html('<div class="card">🎉 Nothing new to suggest right now. Your plan is already close to what you eat.</div>')
    elif sw["i"] < len(cands):
        g = cands[sw["i"]]
        prods = M.products_for(g, p["allergens"])
        pics = photos(g)
        first_with_photo = next((pr for pr in prods if pr.get("image")), None)
        cap = (f'<div class="cap">Example product: {escape(first_with_photo["name"].title() if first_with_photo["name"].isupper() else first_with_photo["name"])}</div>'
               if first_with_photo else "")
        # if a photo fails to load, try the next product's photo; if all fail, show the food icon
        img = (f'<img src="{escape(pics[0])}" alt="" data-alts="{escape("|".join(pics[1:]))}" '
               "onerror=\"var a=(this.dataset.alts||'').split('|').filter(Boolean);"
               "if(a.length){this.src=a.shift();this.dataset.alts=a.join('|');}else{this.remove();}\">") if pics else ""
        reasons = M.why_good(g)
        price_day = float(R["more"][g]) / 100 * M.price(p["scenario"])[M.groups.index(g)]
        examples = ", ".join(pr["name"].title() if pr["name"].isupper() else pr["name"] for pr in prods[:2])
        html(f'<div class="swipe-count">{sw["i"] + 1} of {len(cands)}</div>')
        # buttons either side of the card for laptops; hidden on phones, where you swipe instead
        left, mid, right = st.columns([1, 7, 1], vertical_alignment="center")
        if left.button("✖", key="swipe_no_side", help="Not for me"):
            sw["no"].append(g); sw["i"] += 1; st.rerun()
        if right.button("❤️", key="swipe_yes_side", help="I'd try it"):
            sw["yes"].append(g); sw["i"] += 1; st.rerun()
        with mid:
          html(f'<div class="swipe-card" id="swipe-card-{sw["i"]}"><div class="photo">{M.icon(g)}{img}{cap}</div><div class="body">'
               f'<div class="title">{escape(friendly(g))}</div>'
               f'<div class="muted">Add about {escape(amount_text(g, R["more"][g]))} a day · about £{price_day:.2f}</div>'
               f'<div class="chips">' + "".join(f"<span>{escape(r_)}</span>" for r_ in reasons) + '</div>'
               + (f'<div class="muted" style="margin-top:.5rem">For example: {escape(examples)}</div>' if examples else "")
               + '</div></div>')
        c1, c2 = st.columns(2)
        if c1.button("✖ Not for me", width="stretch", key="swipe_no"):
            sw["no"].append(g); sw["i"] += 1; st.rerun()
        if c2.button("❤️ I'd try it", type="primary", width="stretch", key="swipe_yes"):
            sw["yes"].append(g); sw["i"] += 1; st.rerun()
        st.caption("On a laptop: click ✖ or ❤️ beside the card, or press the ← and → arrow keys.")
        # swipe gestures: drag the card left or right on a phone, or use the arrow keys on a computer
        components.html("""
<script>
const doc = window.parent.document;
function press(label) {
  const b = Array.from(doc.querySelectorAll('button')).find(x => x.innerText.includes(label));
  if (b) b.click();
}
function bind() {
  const card = doc.querySelector('.swipe-card');
  if (!card || card.dataset.bound === card.id) return;
  card.dataset.bound = card.id;
  card.style.transform = ''; card.style.opacity = 1;      // a new card always starts visible
  let x0 = null, dx = 0;
  const start = e => { x0 = (e.touches ? e.touches[0].clientX : e.clientX); };
  const move = e => { if (x0 === null || !doc.body.contains(card)) return; dx = (e.touches ? e.touches[0].clientX : e.clientX) - x0;
                      card.style.transform = `translateX(${dx}px) rotate(${dx / 18}deg)`; };
  const end = () => { if (x0 === null) return;
    const restore = () => setTimeout(() => { card.style.transform = ''; card.style.opacity = 1; }, 1500);
    if (dx > 90) { card.style.transform = 'translateX(600px) rotate(25deg)'; card.style.opacity = 0; setTimeout(() => press("I'd try it"), 180); restore(); }
    else if (dx < -90) { card.style.transform = 'translateX(-600px) rotate(-25deg)'; card.style.opacity = 0; setTimeout(() => press('Not for me'), 180); restore(); }
    else { card.style.transform = ''; }
    x0 = null; dx = 0; };
  card.addEventListener('touchstart', start, {passive: true}); card.addEventListener('touchmove', move, {passive: true});
  card.addEventListener('touchend', end); card.addEventListener('mousedown', start);
  doc.addEventListener('mousemove', move); doc.addEventListener('mouseup', end);
}
if (!doc.__swipeKeys) { doc.__swipeKeys = true;
  doc.addEventListener('keydown', e => { if (!doc.querySelector('.swipe-card')) return;
    if (e.key === 'ArrowRight') press("I'd try it"); if (e.key === 'ArrowLeft') press('Not for me'); }); }
setInterval(bind, 400);
</script>""", height=0)
        st.caption("Photos and product names: Open Food Facts (CC BY-SA). Check labels for allergens.")
    else:
        yes_n, no_n = [friendly(g) for g in sw["yes"]], [friendly(g) for g in sw["no"]]
        html(f'<div class="card"><b>All done! 🎉</b><br>'
             f'<span class="muted">❤️ You\'d try: {escape(", ".join(yes_n) or "nothing yet")}<br>'
             f'✖ Not for you: {escape(", ".join(no_n) or "nothing")}</span></div>')
        if st.button("Update my plan", type="primary", width="stretch"):
            p["liked_groups"] = sorted(set(p["liked_groups"]) | set(sw["yes"]))
            p["excluded_groups"] = sorted(set(p["excluded_groups"]) | set(sw["no"]))
            with st.spinner("Updating your plan..."):
                save_profile_and_replan()
            sw.update({"i": 0, "yes": [], "no": [], "for": None})
            st.success("Done. Your plan now leaves out what you said no to, and leans on what you'd try.")
            st.rerun()
        if st.button("Start again", width="stretch"):
            sw.update({"i": 0, "yes": [], "no": []})
            st.rerun()
    if p["excluded_groups"]:
        with st.expander(f"Foods you've said no to ({len(p['excluded_groups'])})"):
            for gname in list(p["excluded_groups"]):
                c1, c2 = st.columns([3, 1])
                c1.write(f"{M.icon(gname)} {friendly(gname)}")
                if c2.button("Undo", key=f"undo_{gname}"):
                    p["excluded_groups"].remove(gname)
                    save_profile_and_replan()
                    st.rerun()

# ----------------------------------------------------------------------- shopping
elif nav == PAGES[2]:
    st.title("Shopping list")
    days = st.select_slider("Shop for", options=[1, 3, 7, 14], value=7, format_func=lambda d: f"{d} day{'s' if d > 1 else ''}")
    sl = shopping_list(days)
    if len(sl):
        st.caption("Tick what you want to buy. After shopping, tap **Paid** and type what you actually paid, "
                   "to compare with our estimate.")
        start_ticked = st.toggle("Start with everything ticked", value=True)
        table = pd.DataFrame({"Buy": start_ticked,
                              "Item": (sl["icon"] + " " + sl["item"] + " · " + sl["amount"]).values,
                              "Predicted £": sl["cost"].round(2).values, "Actual £": [None] * len(sl),
                              "Aisle": sl["aisle"].values})
        edited = st.data_editor(
            table, hide_index=True, width="stretch", key=f"shop_{days}_{start_ticked}",
            column_order=["Buy", "Predicted £", "Actual £", "Item", "Aisle"],
            disabled=["Item", "Predicted £", "Aisle"],
            column_config={"Buy": st.column_config.CheckboxColumn("✓", width="small"),
                           "Item": st.column_config.TextColumn("Item", width="medium"),
                           "Predicted £": st.column_config.NumberColumn("Estimate", format="£%.2f", width="small"),
                           "Actual £": st.column_config.NumberColumn("Paid", min_value=0.0, max_value=100.0, step=0.01,
                                                                     format="£%.2f", width="small"),
                           "Aisle": st.column_config.TextColumn("Aisle", width="small")})
        chosen = edited[edited["Buy"]]
        predicted = float(chosen["Predicted £"].sum())
        actual_known = chosen["Actual £"].notna()
        actual = float(chosen.loc[actual_known, "Actual £"].sum())
        pred_for_known = float(chosen.loc[actual_known, "Predicted £"].sum())
        diff = actual - pred_for_known
        html(f'<div class="kpis"><div class="kpi"><div class="v">{len(chosen)}</div><div class="l">items chosen</div></div>'
             f'<div class="kpi"><div class="v">£{predicted:.2f}</div><div class="l">our estimate</div></div>'
             f'<div class="kpi"><div class="v">{"£%.2f" % actual if actual_known.any() else "–"}</div>'
             f'<div class="l">you paid{" (" + str(int(actual_known.sum())) + " items)" if actual_known.any() else ""}</div></div></div>')
        if actual_known.any() and pred_for_known > 0:
            word = "more" if diff > 0 else "less"
            html(f'<div class="card">🧾 For the {int(actual_known.sum())} items you priced, you paid <b>£{abs(diff):.2f} {word}</b> '
                 f'than our estimate ({100 * diff / pred_for_known:+.0f}%).</div>')
        c1, c2 = st.columns(2)
        csv = chosen.drop(columns=["Buy"]).rename(columns={"Predicted £": "Estimate £", "Actual £": "Paid £"}).to_csv(index=False)
        c1.download_button("⬇️ Download list", csv, file_name=f"shopping_list_{date.today():%Y-%m-%d}.csv", width="stretch")
        if is_account():
            if c2.button("💾 Save this shop", type="primary", width="stretch"):
                db.save_shopping(ss.user_id, date.today().isoformat(), days,
                                 chosen.drop(columns=["Buy"]).to_dict(orient="records"), predicted,
                                 actual if actual_known.any() else None)
                st.success("Saved to your shopping history.")
            past = db.get_shopping(ss.user_id)
            if past:
                with st.expander(f"🗂️ Your saved shops ({len(past)})"):
                    hist = pd.DataFrame(past, columns=["Date", "Days", "Items", "Estimate £", "Paid £"])
                    st.dataframe(hist, hide_index=True, width="stretch",
                                 column_config={"Estimate £": st.column_config.NumberColumn(format="£%.2f"),
                                                "Paid £": st.column_config.NumberColumn(format="£%.2f")})
                    priced = hist.dropna(subset=["Paid £"])
                    if len(priced) >= 2:
                        st.line_chart(priced.set_index("Date")[["Estimate £", "Paid £"]], height=200, color=["#2E7D32", "#FFA000"])
        else:
            c2.button("💾 Save (needs an account)", disabled=True, width="stretch")
        st.caption("Estimates use average UK supermarket prices (Office for National Statistics). "
                   "Amounts are what you eat, so buy a little extra for peel, bones and cooking.")

# ----------------------------------------------------------------------- progress (dashboard + check in)
elif nav == PAGES[3]:
    html(f'<div class="date">{date.today():%A %d %B %Y}</div>')
    st.title("Your progress")
    weekly = 7 * (R["usual_cost"] - R["cost"])
    html(f'<div class="kpis"><div class="kpi"><div class="v">{N_PLAN}/{len(SHOWN_T)}</div><div class="l">goals met (now {N_NOW})</div></div>'
         f'<div class="kpi"><div class="v">£{R["cost"]:.2f}</div><div class="l">a day</div></div>'
         f'<div class="kpi"><div class="v">{"£%.2f" % abs(weekly)}</div><div class="l">{"saved" if weekly >= 0 else "extra"} a week</div></div></div>')
    n0, n1 = R["now"], R["plan"]
    html('<div class="card bars"><div class="tag" style="color:#1B5E20">How your day changes</div>'
         + bar("🌾 Fibre", n0["fibre"], n1["fibre"], 30, "g", True, 40)
         + bar("🥦 Fruit and veg", n0["fv"], n1["fv"], 5, "portions", True, 8)
         + bar("🍬 Added sugar", n0["free_sugar_pct"], n1["free_sugar_pct"], 5, "% of calories", False, 20)
         + bar("🧈 Saturated fat", n0["sat_fat_pct"], n1["sat_fat_pct"], 11, "% of calories", False, 20)
         + bar("🧂 Salt", n0["salt"], n1["salt"], 6, "g", False, 10)
         + bar("💪 Iron", n0["iron"], n1["iron"], 14.8 if p["age"] <= 50 else 8.7, "mg", True, 20)
         + '<div class="muted" style="margin-top:.4rem">Grey: your usual day · colour: your plan · black line: the healthy goal</div></div>')
    with st.expander("What do these goals mean?"):
        for t in SHOWN_T:
            st.markdown(f"**{'✅' if plan_t[t] else '◻️'} {plain(t)}:** {PLAIN[t][1]}.")
    c1, c2 = st.columns(2)
    with c1:
        items_card("more", "Eat more", R["more"].head(4))
    with c2:
        items_card("less", "Eat less", R["less"].head(4))
    st.subheader("✅ Daily check in")
    if not is_account():
        html('<div class="card">📈 Checking in needs an account so your progress can be saved.<br>'
             '<span class="muted">Guest mode never saves anything.</span></div>')
    else:
        _, saved = db.get_plan(ss.user_id)
        saved = saved or {}
        swaps = ([f"More {friendly(k).lower()}" for k in saved.get("more", {})][:5]
                 + [f"Less {friendly(k).lower()}" for k in saved.get("less", {})][:5])
        day = st.date_input("Day", value=date.today(), max_value=date.today(), format="DD/MM/YYYY")
        with st.form("checkin"):
            st.write(f"**Which swaps did you manage on {day:%A %d %B}?**")
            results = {s_: st.checkbox(s_) for s_ in swaps}
            amount = st.number_input("What did you spend on food? (optional, £ per person)", 0.0, 100.0, 0.0, step=0.5)
            if st.form_submit_button("Save today", type="primary", width="stretch"):
                db.save_checkin(ss.user_id, day.isoformat(), results, amount if amount > 0 else None)
                st.success("Saved. Well done for checking in!")
        checks, spend = db.history(ss.user_id)
        if checks:
            h = pd.DataFrame(checks, columns=["day", "swap", "done"])
            days_in = h["day"].nunique()
            badge = "🥇" if days_in >= 7 else ("🥈" if days_in >= 3 else "🌱")
            html(f'<div class="card">{badge} <b>{days_in} day{"s" if days_in != 1 else ""} checked in</b> in the last two weeks · '
                 f'you managed {100 * h["done"].mean():.0f}% of your swaps</div>')
            st.bar_chart(h.groupby("day")["done"].mean().mul(100).rename("% of swaps managed"), height=200, color="#43A047")
            rate = h.groupby("swap")["done"].agg(["mean", "size"])
            hard = rate[(rate["size"] >= 3) & (rate["mean"] < 0.3)].index.tolist()
            if hard:
                st.info("You're finding these hard: " + ", ".join(hard) + ". Try **✨ Discover** and swipe left on them, "
                        "and the plan will find another way.")
        if spend:
            s_df = pd.DataFrame(spend, columns=["day", "Spent £"]).set_index("day")
            s_df["Budget £"] = R["budget"]
            st.line_chart(s_df, height=200, color=["#2E7D32", "#FFA000"])

# ----------------------------------------------------------------------- money
elif nav == PAGES[4]:
    st.title("Money")
    with st.spinner("Calculating..."):
        pts = [(D, M.cheapest_within(R["xh"], p["scenario"], p["diet"], p["dislikes"], p["age"], D, p["excluded_groups"]))
               for D in [20, 30, 50, 80, 100]]
    ok = dict((D, c) for D, c in pts if c is not None)
    html(f'<div class="kpis"><div class="kpi"><div class="v">£{R["budget"]:.2f}</div><div class="l">your budget a day</div></div>'
         f'<div class="kpi"><div class="v">£{R["cost"]:.2f}</div><div class="l">your plan</div></div>'
         f'<div class="kpi"><div class="v">{"£%.2f" % ok[50] if 50 in ok else "–"}</div><div class="l">cheapest healthy day*</div></div></div>')
    st.caption("*A day that meets every goal while changing about half of what you usually eat.")
    with st.expander("Why does my plan cost this much?"):
        st.write(f"Your budget is **£{R['budget']:.2f} a day**. {BUDGET_WHY}")
        st.write("Your plan spends up to your budget on the healthy foods closest to what you like. "
                 "A cheaper healthy day is possible, but it usually means changing more of what you eat.")
    if ok:
        st.subheader("Spend less by changing more")
        df = pd.DataFrame(sorted(ok.items()), columns=["% of your usual day changed", "Cheapest healthy day £"])
        df["Your budget £"] = R["budget"]
        st.line_chart(df.set_index("% of your usual day changed"), height=240, color=["#2E7D32", "#FFA000"])
        st.caption("Keeping more of your usual food costs more. Changing more of it can make a healthy day cheaper.")
        if 50 in ok and ok[50] < R["budget"] - 0.05:
            if st.button(f"💸 Plan on £{ok[50]:.2f} a day instead", width="stretch"):
                p["weekly_spend"] = round(7 * ok[50] + 0.05, 2)
                save_profile_and_replan()
                st.rerun()
    missing = [D for D, c in pts if c is None]
    if missing:
        st.caption(f"Changing only {', '.join(map(str, missing))}% of your day isn't enough to meet every goal.")
    with st.expander("📈 How food prices have changed"):
        rows = [{"Prices from": SC_LABEL[sc], "Your usual day £": float(R["xh"] @ M.price(sc)),
                 "Your plan £": float(R["x"] @ M.price(sc))} for sc in ["A", "B", "C"]]
        st.dataframe(pd.DataFrame(rows).round(2), hide_index=True, width="stretch")
        st.caption("The same food at average UK prices in 2021, 2023 and 2025 (Office for National Statistics).")

# ----------------------------------------------------------------------- me (profile + help)
elif nav == PAGES[5]:
    st.title("Me")
    src = "your own figure" if p["weekly_spend"] else f"typical for a {BANDS[p['tertile'] - 1].lower()} income household"
    html(f'<div class="card">'
         f'<div class="item"><div class="ic">👤</div><div><div class="nm">Age {p["age"]}</div><div class="am">{p["adults"]} adult(s), {p["children"]} child(ren) · eats {p["meals_per_day"]} times a day</div></div></div>'
         f'<div class="item"><div class="ic">💷</div><div><div class="nm">£{budget_of(p):.2f} a day (£{7 * budget_of(p):.2f} a week)</div><div class="am">{src}</div></div></div>'
         f'<div class="item"><div class="ic">🥗</div><div><div class="nm">{p["diet"]}</div><div class="am">Loves: {", ".join(p["loves"]) or "none"} · Avoids: {", ".join(p["dislikes"]) or "none"}</div></div></div>'
         f'</div>')
    if st.button("✏️ Edit my answers", type="primary", width="stretch"):
        ss.step, ss.plan = 1, None
        go("survey")
    with st.expander("❓ How does this app work?"):
        html('<div class="faq">'
             '<p><b>Where do the suggestions come from?</b><br>From what thousands of UK women actually eat, in the government\'s '
             'National Diet and Nutrition Survey. The app learns which foods people like and keep buying, then finds the smallest '
             'changes that meet the UK\'s healthy eating goals.</p>'
             '<p><b>Why does it keep my favourite foods?</b><br>Big diet changes rarely last. The app changes as little as it can, '
             'and keeps the foods you told us you love.</p>'
             '<p><b>Where do the prices come from?</b><br>Average UK supermarket prices from the Office for National Statistics. '
             'Your shop may be a little different, so you can type what you paid in the shopping list.</p>'
             '<p><b>Is my information safe?</b><br>As a guest, nothing is saved. With an account, only your answers are kept on this '
             'computer, never your actual pay, and you can delete everything at any time.</p>'
             '<p><b>Is this medical advice?</b><br>No. It\'s a university research prototype. It isn\'t for pregnancy, breastfeeding or '
             'medical diets. If you have health worries, speak to your GP.</p></div>')
    if st.button("Log out" if is_account() else "End guest session", width="stretch"):
        ss.user_id, ss.profile, ss.plan, ss.guest = None, None, None, False
        go("welcome")
    if is_account():
        with st.expander("Delete my account"):
            st.write("This permanently deletes your account, answers, plan, check ins and saved shops.")
            if st.button("Delete everything", type="primary"):
                db.delete_user(ss.user_id)
                ss.user_id, ss.profile, ss.plan = None, None, None
                go("welcome")
