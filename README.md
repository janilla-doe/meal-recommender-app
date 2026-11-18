# Research prototype: healthy food plans that fit your budget

A Streamlit **web app** (runs in a browser on a computer or phone) that runs the dissertation's
Stage 3 recommender for one person: learned food preferences, a penalty for changing usual habits,
seven UK dietary targets, a do no harm rule for calcium and iron, and a food budget.

## What it does

1. **Welcome** screen with a short animation and safety notice
2. **Log in, create an account, or continue as a guest.** Guest mode saves nothing.
3. **Set up survey (4 steps):** age, household size, meals a day; take home pay or income band, own food
   spend, price year; diet type, allergens, foods loved and disliked; a usual day (6 sliders)
4. **Plan:** cost now vs plan vs budget, the 7 targets, eat more / eat less in portions, why, example products
5. **Meals:** the plan split into the number of meals the user eats, using when women in the study eat each food
6. **What healthy costs:** the user's own cost curve (cost against how much of the day changes)
7. **Track** (accounts only): tick the swaps managed each day, record spend, see two week progress; swaps
   that are rarely managed are flagged
8. **Profile:** edit answers, log out, delete account

## Privacy

* **Guest mode never creates or writes the database** (there is a test that proves it). Use guest mode for the
  UREC2 user study.
* Accounts are stored in `data/users.db` (SQLite) on the computer running the app: usernames only, passwords as
  salted PBKDF2 hashes, and **income band only, never actual pay**. "Delete my account" removes everything.
* `data/` holds no NDNS respondent data, only group averages and model parameters (notebook 13).

## Run it

1. Run notebook `13_export_app_data.ipynb` once. It writes four small files into `app/data/`.
2. In the Anaconda Prompt:

```
conda activate mealrec
cd path\to\dissertiondata\app
streamlit run app.py
```

It opens at http://localhost:8501.

## Test it

```
pip install pytest
cd path\to\dissertiondata\app
pytest -q
```

Nine tests check the budget and energy limits, vegetarian and dislikes, meal splitting, income bands,
allergen filtering, password hashing, that pay is never stored, account deletion, and both journeys
(guest and account) end to end.

## Use it on a phone

* **Same Wi-Fi:** open the "Network URL" Streamlit prints (for example `http://192.168.1.20:8501`).
* **Anywhere:** deploy free on Streamlit Community Cloud from a GitHub repository. Check with the supervisor
  that the aggregated files in `app/data` are acceptable under the UK Data Service licence first, and do not
  upload `users.db`.
* **App icon:** open the link and choose "Add to Home Screen".

## Notes

* The income bands use approximate cut offs in `model.py` (`INCOME_TERTILE_CUTS`). Check them against the latest
  ONS household disposable income release and cite the source in the dissertation.
* Not medical or dietetic advice. Not for pregnancy, breastfeeding or medical diets.
