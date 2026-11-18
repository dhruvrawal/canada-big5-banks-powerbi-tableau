# Tableau – Fraud & Loan Risk Explorer (build guide)

Use **Tableau Public** (free). Data from `../bi/` (PySpark-built). All data is synthetic.
Tableau Public cannot connect to databases, so use the pre-aggregated CSV marts; they keep the workbook small and fast.

## Data sources
| Sheet group | File |
|---|---|
| Spend & fraud | `mart_monthly_spend_fraud.csv` (relate to `dim_bank.csv` on bank_id) |
| Loan risk | `mart_loan_risk.csv` |
| Scorecard | `mart_bank_scorecard.csv` |

## Calculated fields
```
Fraud Rate %     = SUM([fraud_txns]) / SUM([txns]) * 100
Default Rate %   = SUM([defaults]) / SUM([loans]) * 100
Avg Txn          = SUM([spend_cad]) / SUM([txns])
Spend MoM %      = (ZN(SUM([spend_cad])) - LOOKUP(ZN(SUM([spend_cad])), -1)) / ABS(LOOKUP(ZN(SUM([spend_cad])), -1))
High Risk Flag   = IF [Default Rate %] > 6 THEN "High" ELSE "Normal" END
```
Parameter `Metric Selector` (Spend / Fraud Rate % / Fraud Loss) + a `CASE` calculation lets one chart switch measures.

## Worksheets
1. **Bank scorecard**: bar chart of customers, deposits, default %, fraud %, churn % per bank (small multiples via Measure Names/Values).
2. **Spend trend**: line by `year_month`, colour = bank, with a trend line and forecast (Analytics pane, 3 months).
3. **Fraud heatmap**: category (rows) × channel (columns), colour = Fraud Rate %.
4. **Default by credit band**: bars by `score_band`, reference line at the portfolio average.
5. **Loan book map**: symbol/filled map by `province`, size = book_cad, colour = Default Rate %.

## Dashboards
- **Dashboard 1 – Fraud & Spend**: sheets 2 + 3 + KPI strip; bank filter applied "to all using this data source"; filter actions from heatmap → trend.
- **Dashboard 2 – Credit Risk**: sheets 4 + 5 + scorecard; highlight action on bank.
- Add a **Story** with 4 points: spend growth, online-shopping fraud, sub-600 default risk, student churn.
Use fixed 1200×800 size, one colour per bank, and a text box stating "Synthetic data".

## Publish
File → Save to Tableau Public → copy the URL into the README and your resume/LinkedIn.
