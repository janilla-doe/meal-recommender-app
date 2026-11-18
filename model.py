"""The recommender model used by the app (same as dissertation Stage 3).

Loads only small aggregated files from app/data; never NDNS respondent data.
"""
import json
from functools import lru_cache
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd

DATA = Path(__file__).parent / "data"
SOLVER = cp.CLARABEL if "CLARABEL" in cp.installed_solvers() else None

UK_ALLERGENS = ["gluten", "milk", "eggs", "fish", "crustaceans", "molluscs", "peanuts", "nuts", "soybeans",
                "sesame-seeds", "celery", "mustard", "lupin", "sulphur-dioxide-and-sulphites"]
TARGETS = ["Fibre 30 g", "Free sugars under 5%", "Saturated fat under 11%", "Salt under 6 g",
           "5 a day", "Red meat under 70 g", "Oily fish 140 g a week"]
DIETS = ["No restrictions", "Vegetarian", "Pescatarian", "No pork"]
OCCASION_ORDER = ["Early snack", "Breakfast", "Morning snack", "Lunch", "Afternoon snack", "Evening meal", "Late snack"]
MEALS_FOR = {2: ["Lunch", "Evening meal"],
             3: ["Breakfast", "Lunch", "Evening meal"],
             4: ["Breakfast", "Lunch", "Afternoon snack", "Evening meal"],
             5: ["Breakfast", "Morning snack", "Lunch", "Afternoon snack", "Evening meal"],
             6: ["Breakfast", "Morning snack", "Lunch", "Afternoon snack", "Evening meal", "Late snack"]}

# Friendly food choices for likes and dislikes, mapped to model food groups by name or component
FOOD_CHOICES = {
    "Fish": {"component": ["Fish"]},
    "Red meat": {"component": ["Red and processed meat"]},
    "Chicken and turkey": {"component": ["Poultry"]},
    "Pies, burgers and sausages": {"component": ["Pies, burgers and sausages"]},
    "Eggs": {"component": ["Eggs"]},
    "Milk and yogurt": {"pattern": r"milk|yogurt|yoghurt|fromage"},
    "Cheese": {"pattern": r"cheese"},
    "Beans and lentils": {"pattern": r"beans|pulse|legume|lentil"},
    "Potatoes": {"component": ["Potatoes"]},
    "Rice and pasta": {"component": ["Rice, pasta and grains"]},
    "Bread": {"component": ["Bread"]},
    "Breakfast cereals": {"component": ["Breakfast cereals"]},
    "Fruit": {"component": ["Fruit"]},
    "Vegetables": {"component": ["Vegetables"]},
    "Sandwiches": {"component": ["Sandwiches"]},
    "Pizza": {"component": ["Pizza"]},
    "Biscuits, cakes and sweets": {"component": ["Sweet foods"]},
    "Crisps and savoury snacks": {"component": ["Savoury snacks"]},
    "Fizzy and sugary drinks": {"pattern": r"soft drinks, with added sugar|squash"},
}
PORTION = {  # group: (grams per portion, household unit)
    "Fresh and frozen fruits": (80, "portion"), "Other vegetables": (80, "portion"),
    "Other: Vegetables and vegetable products and dishes": (80, "portion"), "Vegetable products and dishes": (80, "portion"),
    "Baked beans": (80, "portion"), "Potatoes, baked, roast or boiled": (150, "medium potato"),
    "Wheat bread, white": (36, "slice"), "Wheat bread, wholemeal": (36, "slice"), "Oily fish": (100, "fillet"),
    "Other: Soup": (250, "bowl"), "Soft drinks, with added sugar, carbonated": (330, "can"),
    "Breakfast cereals, with added sugar": (30, "bowl"), "Breakfast cereals, porridge style, no added sugar": (40, "bowl of oats"),
    "Semi-skimmed milk (1.8% fat)": (200, "glass"), "Eggs": (60, "egg"),
}
PLAIN = {"Fibre 30 g": ("Enough fibre", "30 g a day keeps you fuller for longer and your gut healthy"),
         "Free sugars under 5%": ("Less added sugar", "sugar added to food and drinks, kept low for teeth and weight"),
         "Saturated fat under 11%": ("Less saturated fat", "the fat in butter, cheese and meat, kept low for your heart"),
         "Salt under 6 g": ("Less salt", "no more than a teaspoon a day, for healthy blood pressure"),
         "5 a day": ("5 fruit and veg a day", "for vitamins, minerals and fibre"),
         "Red meat under 70 g": ("Not too much red meat", "no more than about 70 g a day, to lower bowel cancer risk"),
         "Oily fish 140 g a week": ("Oily fish once a week", "a portion of salmon, mackerel or sardines, for a healthy heart")}

ICON = {"Bread": "🍞", "Sandwiches": "🥪", "Breakfast cereals": "🥣", "Rice, pasta and grains": "🍝", "Pizza": "🍕",
        "Potatoes": "🥔", "Red and processed meat": "🥩", "Pies, burgers and sausages": "🍔", "Poultry": "🍗",
        "Fish": "🐟", "Eggs": "🥚", "Nuts, seeds and meat alternatives": "🥜", "Vegetables": "🥦", "Fruit": "🍎",
        "Dairy": "🥛", "Fats, sauces and condiments": "🧈", "Sweet foods": "🍪", "Savoury snacks": "🥨", "Drinks": "🥤"}
FRIENDLY = {
    "Other vegetables": "Vegetables", "Other: Vegetables and vegetable products and dishes": "Vegetable dishes",
    "Vegetable products and dishes": "Vegetable sides (coleslaw, mixed veg)", "Fresh and frozen fruits": "Fruit, fresh or frozen",
    "Potatoes, baked, roast or boiled": "Potatoes (baked, boiled or roast)", "Other: Soup": "Soup",
    "Wheat bread, white": "White bread", "Wheat bread, wholemeal": "Wholemeal bread", "Wheat bread, mixed grain": "Seeded or mixed grain bread",
    "Soft drinks, with added sugar, carbonated": "Sugary fizzy drinks", "Other: Soft drinks, with added sugar": "Sugary still drinks and squash",
    "Coffee beverages made with all cows' milk, no added sugar": "Milky coffee (latte, cappuccino)",
    "Semi-skimmed milk (1.8% fat)": "Semi skimmed milk", "Whole milk (3.8% fat)": "Whole milk",
    "Breakfast cereals, with added sugar": "Breakfast cereal", "Breakfast cereals, porridge style, no added sugar": "Porridge oats",
    "Sandwiches, meat-based": "Meat sandwiches", "Sandwiches, egg and or cheese": "Egg or cheese sandwiches",
    "Chips and fried potatoes": "Chips", "Sweet biscuits": "Biscuits", "Buns, cakes and pastries": "Cakes and pastries",
    "Chocolate confectionery": "Chocolate", "Crisps and savoury snacks, not nut-based": "Crisps",
    "Pasta, wheat-based, white": "Pasta", "Rice grain and flour, white": "Rice", "Oily fish": "Oily fish (sardines, mackerel, salmon)",
    "Poultry": "Chicken or turkey", "Hard cheese": "Cheese", "Butter and ghee": "Butter", "Eggs": "Eggs",
    "Yogurt and fromage frais, with additions": "Flavoured yogurt", "Fruit and vegetable juices": "Fruit juice",
    "Other: Tea, coffee and water": "Tea, coffee and water", "Other foods": "Other foods",
}
HIDE_IN_MEALS = {"Other: Tea, coffee and water", "Other foods"}


def friendly(group):
    if group in FRIENDLY:
        return FRIENDLY[group]
    name = group.replace("Other: ", "")
    for a, b in [(" and vegetable products and dishes", " dishes"), (" products and dishes", " dishes"),
                 (", with added sugar", ""), (", no added sugar", ""), (" (with bread)", " in a bun")]:
        name = name.replace(a, b)
    return name[0].upper() + name[1:]


def amount_text(group, grams):
    g_, unit = PORTION.get(group, (None, None))
    if g_:
        n = round(abs(grams) / g_ * 2) / 2
        if n < 0.5:
            return f"a little ({abs(grams):.0f} g)"
        n_txt = f"{n:g}"
        return f"{n_txt} {unit}{'s' if n > 1 else ''} ({abs(grams):.0f} g)"
    return f"{abs(grams):.0f} g"


# Approximate equivalised disposable income cut offs (GBP a year) for income thirds.
# Assumption: about 0.75 and 1.3 times a UK median of roughly GBP 34,500 (ONS). Check against the latest
# ONS "Household disposable income and inequality" release before reporting.
INCOME_TERTILE_CUTS = (26000, 45000)


@lru_cache(maxsize=1)
def load():
    g = pd.read_csv(DATA / "groups.csv", index_col=0)
    s = json.loads((DATA / "settings.json").read_text())
    p = json.loads((DATA / "products.json").read_text()) if (DATA / "products.json").exists() else {}
    occ_path = DATA / "group_occasions.csv"
    occ = pd.read_csv(occ_path, index_col=0).reindex(g.index) if occ_path.exists() else None
    return g, s, p, occ


def groups_for(choice, G):
    rule = FOOD_CHOICES[choice]
    if "component" in rule:
        mask = G["component"].isin(rule["component"])
    else:
        mask = G.index.str.contains(rule["pattern"], case=False, regex=True)
    return list(G.index[mask])


def income_tertile(monthly_take_home, adults, children):
    """Equivalise household take home pay (modified OECD scale) and place it in an income third."""
    scale = 1 + 0.5 * max(adults - 1, 0) + 0.3 * children
    yearly_eq = 12 * monthly_take_home / scale
    lo, hi = INCOME_TERTILE_CUTS
    return 1 if yearly_eq < lo else (2 if yearly_eq < hi else 3)


class Model:
    def __init__(self):
        self.G, self.S, self.PRODUCTS, self.OCC = load()
        G = self.G
        self.groups = list(G.index)
        self.m = len(self.groups)
        c = lambda n: G[n].values
        self.KCAL, self.FIB, self.FS, self.SF, self.NA = (c(n) for n in ["Energykcal_100g", "AOACFibreg_100g",
                                                                        "FreeSugarsg_100g", "Saturatedfattyacidsg_100g", "Sodiummg_100g"])
        self.FV = ((G["Fruitg_100g"] + G["Tomatoesg_100g"] + 5 * G["TomatoPureeg_100g"] + G["Brassicaceaeg_100g"]
                    + G["YellowRedGreeng_100g"] + G["OtherVegg_100g"]) / 80 + G["DriedFruitg_100g"] / 30).values
        self.JUICE = (G["FruitJuiceg_100g"] + G["SmoothieFruitg_100g"]).values
        self.BEANS = c("Beansg_100g")
        self.RED = G[["Beefg_100g", "Lambg_100g", "Porkg_100g", "ProcessedRedMeatg_100g", "OtherRedMeatg_100g",
                      "Burgersg_100g", "Sausagesg_100g", "Offalg_100g"]].sum(axis=1).values
        self.OILY, self.CA, self.FE = c("OilyFishg_100g"), c("Calciummg_100g"), c("Ironmg_100g")
        self.C, self.Q = c("c"), c("q")
        self.UPPER, self.AVG, self.FIXED = c("upper_100g"), c("avg_100g"), c("fixed").astype(float)
        name = pd.Series(self.groups)
        meat_fish = G["meat_or_fish"].astype(bool).values
        fish = (G["component"] == "Fish").values | name.str.contains(r"fish|tuna|shellfish", case=False).values
        pork = name.str.contains(r"pork|bacon|ham|sausage|gammon", case=False).values
        self.EXCLUDE = {"No restrictions": np.zeros(self.m, bool), "Vegetarian": meat_fish,
                        "Pescatarian": meat_fish & ~fish, "No pork": pork}

    # ------------------------------------------------------------ helpers
    def price(self, scenario):
        return self.G[f"price_{scenario}"].values

    def budget_for(self, scenario, tertile):
        return self.S["budgets"][scenario][str(int(tertile))]

    def blocked(self, diet, dislikes, excluded_groups=()):
        mask = self.EXCLUDE[diet].copy()
        for ch in dislikes:
            for gname in groups_for(ch, self.G):
                mask[self.groups.index(gname)] = True
        for gname in excluded_groups:
            if gname in self.groups:
                mask[self.groups.index(gname)] = True
        return mask

    def usual_day(self, diet="No restrictions", dislikes=(), sliders=None):
        """The typical day for women in the study, adjusted by the user's diet, dislikes and answers."""
        xh = self.AVG.copy()
        xh[self.blocked(diet, dislikes)] = 0
        sliders = sliders or {}
        def setg(name, grams):
            if name in self.groups and not self.blocked(diet, dislikes)[self.groups.index(name)]:
                xh[self.groups.index(name)] = grams / 100
        if "fruit" in sliders: setg("Fresh and frozen fruits", 80 * sliders["fruit"])
        if "veg" in sliders: setg("Other vegetables", 80 * sliders["veg"])
        if "white_bread" in sliders: setg("Wheat bread, white", 36 * sliders["white_bread"])
        if "brown_bread" in sliders: setg("Wheat bread, wholemeal", 36 * sliders["brown_bread"])
        if "fizzy" in sliders: setg("Soft drinks, with added sugar, carbonated", 330 * sliders["fizzy"])
        if "sweet" in sliders:
            sw = (self.G["component"] == "Sweet foods").values & ~self.blocked(diet, dislikes)
            now = 100 * xh[sw].sum()
            if now > 0:
                xh[sw] *= (30 * sliders["sweet"]) / now
        return xh

    def nutrients(self, x):
        kcal = float(x @ self.KCAL)
        return {"kcal": kcal, "fibre": float(x @ self.FIB),
                "free_sugar_pct": 100 * 3.75 * float(x @ self.FS) / max(kcal, 1),
                "sat_fat_pct": 100 * 9 * float(x @ self.SF) / max(kcal, 1), "salt": 2.5 * float(x @ self.NA) / 1000,
                "fv": float(x @ self.FV + min(x @ self.JUICE, 150) / 150 + min(x @ self.BEANS, 80) / 80),
                "red": float(x @ self.RED), "oily": float(x @ self.OILY),
                "calcium": float(x @ self.CA), "iron": float(x @ self.FE)}

    def targets_met(self, n, drop_oily):
        tol = 0.005
        met = [n["fibre"] >= 30 * (1 - tol), n["free_sugar_pct"] <= 5 * (1 + tol), n["sat_fat_pct"] <= 11 * (1 + tol),
               n["salt"] <= 6 * (1 + tol), n["fv"] >= 5 * (1 - tol), n["red"] <= 70 * (1 + tol),
               None if drop_oily else n["oily"] >= 20 * (1 - tol)]
        return dict(zip(TARGETS, met))

    # ------------------------------------------------------------ optimisation
    def _base(self, x, xh, blocked, iron_rni):
        e = xh @ self.KCAL
        kx = self.KCAL @ x
        up = np.where(blocked, 0, np.maximum(self.UPPER, xh))
        return [kx >= 0.9 * e, kx <= 1.1 * e, x <= up, cp.multiply(self.FIXED * (~blocked), x - xh) == 0,
                self.CA @ x >= min(self.S["calcium_rni"], xh @ self.CA), self.FE @ x >= min(iron_rni, xh @ self.FE)]

    def _terms(self, x, drop_oily):
        kx = self.KCAL @ x
        terms = [(self.FIB @ x, ">=", 30), (3.75 * (self.FS @ x) - 0.05 * kx, "<=", 0),
                 (9 * (self.SF @ x) - 0.11 * kx, "<=", 0), (2.5 * (self.NA @ x) / 1000, "<=", 6),
                 (self.FV @ x + cp.minimum(self.JUICE @ x, 150) / 150 + cp.minimum(self.BEANS @ x, 80) / 80, ">=", 5),
                 (self.RED @ x, "<=", 70)]
        if not drop_oily:
            terms.append((self.OILY @ x, ">=", 20))
        return terms

    @staticmethod
    def age_band(age):
        return "19 to 50" if (age if isinstance(age, (int, float)) else 30) <= 50 else "51 to 64"

    def plan(self, xh, scenario, budget, diet="No restrictions", dislikes=(), loves=(), age=30,
             liked_groups=(), excluded_groups=(), day_seed=None, variety=0.4):
        """Best plan for one day. With day_seed, the learned preferences are nudged a little at random
        (the same nudge for the same day), so each day differs while every day still meets the goals,
        fits the budget and stays close to what she likes."""
        blocked = self.blocked(diet, dislikes, excluded_groups)
        oily_ok = (self.OILY > 1) & ~blocked
        drop_oily = not oily_ok.any()
        iron_rni = self.S["iron_rni_19_50"] if self.age_band(age) == "19 to 50" else self.S["iron_rni_51_64"]
        price = self.price(scenario)
        habit_w = np.full(self.m, 1.0)
        for ch in loves:                        # loved foods: five times harder to move away from
            for gname in groups_for(ch, self.G):
                habit_w[self.groups.index(gname)] = 5.0
        for gname in liked_groups:              # foods she said she'd try: half the cost of adding them
            if gname in self.groups:
                habit_w[self.groups.index(gname)] = min(habit_w[self.groups.index(gname)], 0.5)
        x = cp.Variable(self.m, nonneg=True)
        terms = self._terms(x, drop_oily)
        slack = cp.Variable(len(terms), nonneg=True)
        scale = np.array([30, 100, 100, 6, 5, 70, 20][:len(terms)])
        soft = [(e + slack[i] >= r) if s == ">=" else (e <= r + slack[i]) for i, (e, s, r) in enumerate(terms)]
        C, target = self.C, xh
        if day_seed is not None:
            rng = np.random.default_rng(int(day_seed))
            C = self.C * np.exp(rng.normal(0, variety, self.m))
            # habit only foods: vary the usual amount a little too, within the realistic limits
            target = np.where(self.C == 0, np.clip(xh * np.exp(rng.normal(0, variety, self.m)), 0, np.maximum(self.UPPER, xh)), xh)
            target = np.where(self.FIXED > 0, xh, target)
        utility = C @ x - 0.5 * cp.sum(cp.multiply(self.Q, cp.square(x)))
        habit = cp.sum(cp.multiply(habit_w * self.KCAL / 100, cp.abs(x - target)))
        prob = cp.Problem(cp.Maximize(utility - self.S["mu"] * habit - 1000 * cp.sum(slack / scale)),
                          self._base(x, xh, blocked, iron_rni) + soft + [price @ x <= budget])
        prob.solve(solver=SOLVER)
        xv = np.clip(x.value, 0, None)
        duals = [abs(float(np.atleast_1d(c.dual_value)[0])) if c.dual_value is not None else 0.0 for c in soft]
        names = TARGETS[:6] + ([] if drop_oily else [TARGETS[6]])
        binding = [names[i] for i, d in enumerate(duals) if d > 1e-6 and slack.value[i] < 1e-4]
        return {"x": xv, "cost": float(xv @ price), "usual_cost": float(xh @ price), "budget": budget,
                "all_met": bool(slack.value.sum() < 1e-4), "binding": binding, "drop_oily": drop_oily,
                "now": self.nutrients(xh), "plan": self.nutrients(xv)}

    def cheapest_within(self, xh, scenario, diet, dislikes, age, change_pct, excluded_groups=()):
        blocked = self.blocked(diet, dislikes, excluded_groups)
        drop_oily = not ((self.OILY > 1) & ~blocked).any()
        iron_rni = self.S["iron_rni_19_50"] if self.age_band(age) == "19 to 50" else self.S["iron_rni_51_64"]
        x = cp.Variable(self.m, nonneg=True)
        hard = [(e >= r) if s == ">=" else (e <= r) for e, s, r in self._terms(x, drop_oily)]
        moved = cp.sum(cp.multiply(self.KCAL, cp.abs(x - xh)))
        prob = cp.Problem(cp.Minimize(self.price(scenario) @ x),
                          self._base(x, xh, blocked, iron_rni) + hard + [moved <= 2 * (xh @ self.KCAL) * change_pct / 100])
        prob.solve(solver=SOLVER)
        return float(prob.value) if prob.status in ("optimal", "optimal_inaccurate") else None

    # ------------------------------------------------------------ presentation
    def swaps(self, xh, x, threshold=15):
        ch = pd.Series((x - xh) * 100, index=self.groups)
        return ch[ch >= threshold].sort_values(ascending=False), ch[ch <= -threshold].sort_values()

    def icon(self, gname):
        return ICON.get(self.G.loc[gname, "component"], "🍽️") if gname in self.G.index else "🍽️"

    def why_good(self, gname):
        """Plain reasons a food group helps, from its nutrients per 100 g."""
        g = self.G.loc[gname]
        j = self.groups.index(gname)
        reasons = []
        if g["AOACFibreg_100g"] >= 3:
            reasons.append("a good source of fibre")
        if self.FV[j] >= 0.6 or g["Beansg_100g"] >= 30:
            reasons.append("counts towards your 5 a day")
        if g["OilyFishg_100g"] >= 30:
            reasons.append("oily fish, good for your heart")
        if g["Ironmg_100g"] >= 1.5:
            reasons.append("adds iron")
        if g["Calciummg_100g"] >= 100:
            reasons.append("adds calcium for strong bones")
        if g["FreeSugarsg_100g"] < 2 and g["Energykcal_100g"] > 20 and not reasons:
            reasons.append("filling without added sugar")
        return reasons or ["helps balance your day"]

    def describe(self, gname, grams):
        return f"{friendly(gname)}: {amount_text(gname, grams)}"

    def split_into_meals(self, x, meals_per_day, min_grams=10):
        """Share each food group across the user's meals, using when women in the study usually eat it."""
        occasions = MEALS_FOR[int(np.clip(meals_per_day, 2, 6))]
        if self.OCC is None:
            share = pd.DataFrame(1 / len(occasions), index=self.groups, columns=occasions)
        else:
            share = self.OCC.reindex(columns=occasions).fillna(0)
            empty = share.sum(axis=1) == 0
            share.loc[empty] = 1 / len(occasions)
            share = share.div(share.sum(axis=1), axis=0)
            # keep each food to the meals where it is mainly eaten, so meals are not spread thinly
            top = share.eq(share.max(axis=1), axis=0)
            share = share.where((share >= 0.25) | top, 0)
            share = share.div(share.sum(axis=1), axis=0)
        grams = share.mul(100 * x, axis=0)
        meals = {}
        for occ in occasions:
            col = grams[occ].drop(labels=[g for g in HIDE_IN_MEALS if g in grams.index]) if min_grams > 0 else grams[occ]
            items = col[col >= min_grams].sort_values(ascending=False)
            meals[occ] = [(gname, float(g)) for gname, g in items.items()]
        return meals

    def products_for(self, gname, avoid):
        return [p for p in self.PRODUCTS.get(gname, []) if not set(p["allergens"]) & set(avoid)][:3]
