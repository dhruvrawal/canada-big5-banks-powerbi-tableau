# Power BI – Big 5 Banks Executive Dashboard (build guide)

Data: the CSVs in `../bi/` (built by `scripts/build_bi_marts.py` with PySpark). All data is synthetic.

## Quick start: open the ready-made project
`Big5_Banks.pbip` (a Power BI Project, text-based so it works with Git) already contains the full model (7 tables, 6 relationships), all DAX measures below, and four report pages (Executive Overview, Fraud Monitor, Credit Risk, Customers and Churn). In Power BI Desktop use **File → Open → Browse this device**, pick `Big5_Banks.pbip`, then click **Refresh now** (twice if the first pass leaves some visuals blank). The CSV paths inside the model are absolute (set for the author's machine, `D:\Work\projects\canada-big5-banks-powerbi-tableau\bi\`). After cloning, open **Transform data**, and for each table edit the first query step (Source) so the path points at your local `bi` folder. Section 4 describes each page; the decomposition tree, filled map, tooltips page and drill-through are optional extras to add by hand.

The manual steps below are the same thing done by hand.

## 1. Load (Get Data → Text/CSV → Transform)
Load: `dim_bank, dim_branch, dim_customer, dim_account, dim_date, fact_transactions, fact_loans`.
In Power Query: set `dim_date[date]`, `fact_transactions[date]`, `dim_customer[join_date]` to **Date**; `amount_cad`, `principal_cad` to **Fixed decimal**; `is_fraud`, `defaulted`, `churned` to **Whole number**.

## 2. Model (star schema, single-direction, one-to-many)
| From (one) | To (many) |
|---|---|
| dim_bank[bank_id] | dim_customer[primary_bank] |
| dim_customer[customer_id] | dim_account[customer_id], fact_loans[customer_id], fact_transactions[customer_id] |
| dim_date[date] | fact_transactions[date] |
| dim_branch[branch_id] | fact_transactions[branch_id] |

(Everything hangs off `dim_customer` so a bank filter reaches every fact table through one path; linking `dim_bank` directly to the facts as well would create ambiguous paths.)

Mark `dim_date` as the date table. Hide key columns in report view. Sort `month_name` by `month_num`.

## 3. DAX measures (create a `_Measures` table)
```DAX
Total Spend = SUM ( fact_transactions[amount_cad] )
Transactions = COUNTROWS ( fact_transactions )
Fraud Txns = SUM ( fact_transactions[is_fraud] )
Fraud Rate % = DIVIDE ( [Fraud Txns], [Transactions] ) * 100
Fraud Loss = CALCULATE ( [Total Spend], fact_transactions[is_fraud] = 1 )

Loan Book = SUM ( fact_loans[principal_cad] )
Loans = COUNTROWS ( fact_loans )
Default Rate % = DIVIDE ( SUM ( fact_loans[defaulted] ), [Loans] ) * 100

Customers = COUNTROWS ( dim_customer )
Churn Rate % = DIVIDE ( SUM ( dim_customer[churned] ), [Customers] ) * 100
Deposits = CALCULATE ( SUM ( dim_account[balance] ), dim_account[account_type] <> "Credit Card" )

Spend LY = CALCULATE ( [Total Spend], SAMEPERIODLASTYEAR ( dim_date[date] ) )
Spend YoY % = DIVIDE ( [Total Spend] - [Spend LY], [Spend LY] ) * 100
Spend MoM % =
VAR prev = CALCULATE ( [Total Spend], DATEADD ( dim_date[date], -1, MONTH ) )
RETURN DIVIDE ( [Total Spend] - prev, prev ) * 100
Market Share % = DIVIDE ( [Customers], CALCULATE ( [Customers], ALL ( dim_bank ) ) ) * 100
Avg Txn Value = DIVIDE ( [Total Spend], [Transactions] )
```

## 4. Pages
**Page 1 – Executive Overview**: KPI cards (Customers, Deposits, Loan Book, Default %, Fraud %, Churn %); clustered bar of Market Share by bank; line chart Spend by `year_month` split by bank; slicers: Year, Bank, Province.

**Page 2 – Fraud Monitor**: Fraud Rate % by category (bar) and by channel (column); matrix category × channel with conditional-format background on Fraud Rate %; line of Fraud Loss by month; top-10 branches by Fraud Rate (Top N filter).

**Page 3 – Credit Risk**: Default Rate % by `score_band` (column, highlight "1. <600"); by loan_type; matrix bank × loan_type; scatter Interest Rate vs Default % by bank; decomposition tree (Default % → score_band → loan_type → province).

**Page 4 – Customers & Churn**: Churn % by segment and age_group; filled map by province (Customers); drill-through page for a bank.

## 5. Polish checklist
Consistent colour per bank across all pages · titles state the insight ("Sub-600 scores default at ~4x the rate") · tooltips page · bookmarks for page navigation · Row-level security role per bank (`[bank_id] = "RBC"`) is a good interview talking point.

## 6. Publish
Save as `Big5_Banks.pbix` in this folder. Publish to Power BI Service (free work/school account) or screenshot each page for the README. A `.pbix` can be committed to GitHub if under 100 MB.
