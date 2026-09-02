# Methodology & Full Write-Up

## 1. Problem Framing

The initial goal was a standard churn prediction project. Early EDA revealed this framing doesn't fit the data: only **3% of customers ever place a second order**, so a subscription-style churn definition ("active, then goes silent") mislabels ~98.6% of customers as "churned" — a label that's technically true but useless for modeling, since predicting "everyone churns" requires no real signal.

**Reframed problem:** predict whether a first-time buyer will make a second purchase, using only information available at the time of their first order.

## 2. Data & Pipeline

- Source: Olist Brazilian E-Commerce dataset (9 relational tables, ~99,441 orders, Sept 2016–Aug 2018)
- Built a SQL pipeline (DuckDB) joining orders, customers, payments, reviews, and products
- **Key gotcha handled:** `customer_id` is unique per *order*, not per *customer* — `customer_unique_id` is the real identifier. Missing this would make every customer look like a one-time buyer.
- **Leakage check:** an earlier version of the feature table aggregated across a customer's *entire* order history (total spend, order count) — since the target is "did they place a second order," this leaked the answer into the features. Rebuilt features to use only first-order information.

## 3. Target Definition & Censoring

- Customers whose first order was too recent (within the 180-day observation window of the dataset's end date) were excluded — an accuracy without this step would incorrectly penalize customers who simply hadn't had time to return yet.
- Final valid cohort: 55,904 customers. Second-purchase rate: **3.97%**.

## 4. Train/Test Split

Used a time-based split (80th percentile purchase date as cutoff) rather than random shuffling, since a random split would let the model train on customers who purchased chronologically *after* some test customers — leaking timeline patterns that wouldn't exist at real prediction time.

Train: 44,723 customers (Oct 2016–Jan 2018) | Test: 11,181 customers (Jan–Mar 2018)

## 5. Predictive Modeling

| Model | ROC-AUC | PR-AUC |
|---|---|---|
| Logistic Regression (baseline) | 0.566 | 0.048 |
| XGBoost | 0.573 | 0.047 |
| XGBoost + review sentiment (NLP) | 0.568 | 0.047 |

**Finding:** neither model family nor added NLP features meaningfully improved prediction. Feature importances were flat (no dominant feature), suggesting the ceiling is data-driven, not model-driven — first-order transactional data has limited signal for predicting return behavior on its own. This is a realistic result: return behavior is likely driven by factors outside this dataset (competing options, changing needs, brand recall).

A small-sample coefficient artifact was also caught and excluded from interpretation: `state_RR` (Roraima) had an outsized coefficient driven by only 19 training examples — a reminder to check sample size behind any standout feature before trusting it.

## 6. Uplift Modeling

Since no real experiment/campaign data exists in the source, a synthetic retention discount treatment was simulated:
- 50/50 random treatment assignment
- Treatment effect designed to be larger for customers with a worse first-order experience (late delivery, low review score) — a plausible, documented marketing pattern, explicitly **not** a measured fact
- Fit a T-learner (two `GradientBoostingClassifier` models — no `causalml` dependency needed)

**Result:** predicted average uplift (0.0405) closely matched true average uplift (0.0410), and the model correctly *ranked* customers by treatment responsiveness — Qini coefficient of **33.9**, clearly above the random-targeting baseline.

## 7. Business Translation

| % Customers Targeted | % Benefit Captured |
|---|---|
| 10% | 25.6% |
| 20% | 38.8% |
| 30% | 46.9% |
| 50% | 62.2% |

**Interpretation:** targeting the top 20% of customers by predicted uplift captures nearly 2x the benefit you'd expect from random targeting at the same cost — a concrete, quantifiable efficiency gain for a retention campaign.

## 8. Key Takeaway

The most important finding isn't a single metric — it's the contrast between two results: **predicting what a customer will do is hard with this data, but predicting how much a specific intervention changes their behavior is tractable.** This distinction (outcome prediction vs. treatment effect estimation) is often more actionable for a business than outcome prediction alone, since it directly answers "who should we spend budget on."

## Limitations & Honest Caveats
- The treatment effect is simulated, not measured from a real experiment — a genuine A/B test would be needed before deploying this in production
- Coefficients/importances for low-population geographic segments (e.g., states with <50 training examples) should not be over-interpreted
- Review sentiment did not add value beyond the existing numeric review score — included as a reported negative result, not a failure to hide