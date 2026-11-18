"""Build a star-schema 'gold' layer with PySpark for Power BI and Tableau.
Run from the project root:  .pyspark-env/Scripts/python.exe scripts/build_bi_marts.py
Outputs single-file CSVs to /bi (synthetic data, see README)."""
import os
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.master("local[*]").config("spark.ui.showConsoleProgress", "false")
         .config("spark.sql.session.timeZone", "UTC").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")
OUT = "bi"
os.makedirs(OUT, exist_ok=True)


def load(n):
    return spark.read.option("header", True).option("inferSchema", True).csv(f"data/{n}.csv")


def save(df, name):
    pdf = df.toPandas()
    pdf.to_csv(f"{OUT}/{name}.csv", index=False)
    print(f"{name}: {len(pdf):,} rows")


banks, branches, cust, acc, tx, loans = [load(n) for n in
    ["banks", "branches", "customers", "accounts", "transactions", "loans"]]

# --- data-quality: dedupe + positive amounts
tx = (tx.dropDuplicates(["txn_id"]).filter(F.col("amount_cad") > 0)
        .withColumn("txn_date", F.to_date("txn_date")))

# --- dimensions
dim_bank = banks
dim_branch = branches
dim_customer = (cust
    .withColumn("score_band", F.when(F.col("credit_score") < 600, "1. <600")
                .when(F.col("credit_score") < 680, "2. 600-679")
                .when(F.col("credit_score") < 740, "3. 680-739").otherwise("4. 740+"))
    .withColumn("age_group", F.when(F.col("age") < 25, "18-24").when(F.col("age") < 35, "25-34")
                .when(F.col("age") < 50, "35-49").when(F.col("age") < 65, "50-64").otherwise("65+"))
    .withColumn("join_date", F.to_date("join_date")))
dim_account = acc.select("account_id", "customer_id", "bank_id", "branch_id", "account_type", "balance")

dates = (tx.agg(F.min("txn_date").alias("a"), F.max("txn_date").alias("b")).collect()[0])
dim_date = (spark.sql(f"SELECT explode(sequence(to_date('{dates.a}'), to_date('{dates.b}'), interval 1 day)) AS date")
    .withColumn("year", F.year("date")).withColumn("quarter", F.concat(F.lit("Q"), F.quarter("date")))
    .withColumn("month_num", F.month("date")).withColumn("month_name", F.date_format("date", "MMM"))
    .withColumn("year_month", F.date_format("date", "yyyy-MM")))

# --- facts (txn enriched with bank/branch so BI tools need fewer joins)
fact_txn = (tx.join(acc.select("account_id", "bank_id", "branch_id", "customer_id"), "account_id")
              .select("txn_id", F.col("txn_date").alias("date"), "account_id", "customer_id",
                      "bank_id", "branch_id", "category", "channel", "amount_cad", "is_fraud"))
fact_loan = loans.select("loan_id", "customer_id", "bank_id", "loan_type", "principal_cad",
                         "interest_rate_pct", "term_months", "defaulted")

# --- pre-aggregated marts (fast for Tableau Public, which has row limits per extract)
mart_monthly = (fact_txn.withColumn("year_month", F.date_format("date", "yyyy-MM"))
    .groupBy("year_month", "bank_id", "category", "channel")
    .agg(F.count("*").alias("txns"), F.round(F.sum("amount_cad"), 2).alias("spend_cad"),
         F.sum("is_fraud").alias("fraud_txns"),
         F.round(F.sum(F.when(F.col("is_fraud") == 1, F.col("amount_cad")).otherwise(0)), 2).alias("fraud_loss_cad")))

mart_loan_risk = (fact_loan.join(dim_customer.select("customer_id", "score_band", "province", "segment"), "customer_id")
    .groupBy("bank_id", "loan_type", "score_band", "province")
    .agg(F.count("*").alias("loans"), F.round(F.sum("principal_cad"), 0).alias("book_cad"),
         F.sum("defaulted").alias("defaults"), F.round(F.avg("interest_rate_pct"), 2).alias("avg_rate_pct")))

mart_scorecard = (dim_customer.groupBy(F.col("primary_bank").alias("bank_id"))
    .agg(F.count("*").alias("customers"), F.round(F.avg("churned") * 100, 2).alias("churn_pct"))
    .join(dim_account.filter(F.col("account_type") != "Credit Card").groupBy("bank_id")
          .agg(F.round(F.sum("balance") / 1e6, 1).alias("deposits_cad_m")), "bank_id")
    .join(fact_loan.groupBy("bank_id").agg(F.round(F.avg("defaulted") * 100, 2).alias("default_rate_pct"),
          F.round(F.sum("principal_cad") / 1e6, 1).alias("loan_book_cad_m")), "bank_id")
    .join(fact_txn.groupBy("bank_id").agg(F.round(F.avg("is_fraud") * 100, 3).alias("fraud_rate_pct"),
          F.round(F.sum("amount_cad") / 1e6, 2).alias("spend_cad_m")), "bank_id"))

for df, n in [(dim_bank, "dim_bank"), (dim_branch, "dim_branch"), (dim_customer, "dim_customer"),
              (dim_account, "dim_account"), (dim_date, "dim_date"), (fact_txn, "fact_transactions"),
              (fact_loan, "fact_loans"), (mart_monthly, "mart_monthly_spend_fraud"),
              (mart_loan_risk, "mart_loan_risk"), (mart_scorecard, "mart_bank_scorecard")]:
    save(df, n)
spark.stop()
