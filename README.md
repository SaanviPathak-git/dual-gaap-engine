# Dual-GAAP Reconciliation Engine (Ind AS ⇌ US GAAP)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://dual-gaap-engine.streamlit.app)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Accounting](https://img.shields.io/badge/Standards-Ind%20AS%20%7C%20US%20GAAP-green.svg)](https://fasb.org)

An automated financial advisory pipeline bridging **Indian Accounting Standards (Ind AS / IFRS-converged)** and **US GAAP** for **ASC 842 (Leases)** and **ASC 326 (CECL Financial Instruments)**.

**[Launch the Interactive Web App](https://dual-gaap-engine.streamlit.app)** to run the reconciliation on sample data or upload custom files.

📌 Project Purpose
During cross-border acquisitions, US capital raises, or SEC reporting readiness (Form 10-K / 20-F), Indian companies must reconcile their statutory financial statements to US GAAP.

Manual reconciliation workbooks in Excel introduce significant audit risk through formula corruption, untracked modifications, and ledger imbalances. This engine automates the conversion process: it ingests statutory trial balances and lease registers, calculates technical GAAP deltas, enforces an automated double-entry audit check, and generates export-ready top-side Journal Vouchers (JVs).

⚖️ Technical Accounting Coverage
1. Lease Accounting: Ind AS 116 ➔ US GAAP ASC 842
Ind AS 116 (Single Finance Model): Lessees treat all leases as financing arrangements, recognizing front-loaded P&L expenses through Straight-Line ROU Amortization ($252,741.83) and Lease Interest Expense ($75,822.55), totaling $328,564.38 in Year 1.

US GAAP ASC 842 (Dual Operating Model): Operating leases require a single straight-line rent expense ($300,000.00).

Automated Adjustment: The engine reverses the financing expense presentation, recognizes straight-line rent, and records a balancing adjustment of $28,564.38 to Accumulated Amortization to re-align the ROU asset carrying value—resulting in a $28,564.38 favorable pre-tax EBITDA variance.

2. Credit Losses: Ind AS 109 ➔ US GAAP ASC 326 (CECL)
Ind AS 109 (Incurred / Staged Model): Stage 1 performing trade receivables require only a 12-Month Expected Credit Loss (ECL) reserve (1.89% = $94,500.00 on $5,000,000 gross receivables).

US GAAP ASC 326 (CECL Lifetime Model): Rejects the 12-month lag and mandates Day-1 Lifetime Expected Credit Losses across all contracts (3.50% = $175,000.00).

Automated Adjustment: The engine records an incremental pre-tax provision of $80,500.00 with an offsetting credit to the contra-asset allowance.

🚀 How to Use
Method 1: Interactive Web App (No Code)
Open the Live Web Application.

Method 2: Google ColabRun the complete pipeline directly in Google Colab:
Bash
!git clone [https://github.com/SaanviPathak-git/dual-gaap-engine.git](https://github.com/SaanviPathak-git/dual-gaap-engine.git)
%cd dual-gaap-engine
!python main.py

   
