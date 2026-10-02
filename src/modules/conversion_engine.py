import os
from typing import Dict, List
import pandas as pd


class GAAPConversionEngine:
    def __init__(self, trial_balance_path: str, lease_contracts_path: str):
        self.trial_balance_path = trial_balance_path
        self.lease_contracts_path = lease_contracts_path

        self.tb_df = self._load_and_clean_csv(self.trial_balance_path)
        self.leases_df = self._load_and_clean_csv(self.lease_contracts_path)

        self.journal_vouchers: List[Dict[str, object]] = []
        self.jv_counter = 1

    @staticmethod
    def _load_and_clean_csv(path: str) -> pd.DataFrame:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Input file not found: {path}")

        df = pd.read_csv(path)
        df.columns = [str(col).strip() for col in df.columns]

        # Force Account_Code to string type so lookups never fail
        if "Account_Code" in df.columns:
            df["Account_Code"] = df["Account_Code"].astype(str).str.strip()

        return df

    @staticmethod
    def calculate_pv_annuity(payment: float, rate: float, periods: int) -> float:
        if rate == 0:
            return round(payment * periods, 2)
        pv = sum(payment / ((1.0 + rate) ** t) for t in range(1, periods + 1))
        return round(pv, 2)

    def _record_jv(self, jv_id, category, account_code, account_name, debit, credit, narration):
        self.journal_vouchers.append({
            "JV_ID": jv_id,
            "Adjustment_Category": category,
            "Account_Code": str(account_code),
            "Account_Name": str(account_name),
            "Debit_USD": round(debit, 2),
            "Credit_USD": round(credit, 2),
            "Narration": narration,
        })

    def process_lease_adjustments(self) -> Dict[str, float]:
        total_ind_as_expense = 0.0
        total_us_gaap_expense = 0.0
        total_delta = 0.0

        for _, row in self.leases_df.iterrows():
            if str(row["US_GAAP_Classification"]).strip().upper() != "OPERATING":
                continue

            contract_id = str(row["Contract_ID"]).strip()
            payment = float(row["Annual_Payment"])
            term = int(row["Term_Years"])
            rate = float(row["Discount_Rate"])

            initial_pv = self.calculate_pv_annuity(payment, rate, term)
            ind_as_amort = round(initial_pv / term, 2)
            ind_as_interest = round(initial_pv * rate, 2)
            ind_as_total = round(ind_as_amort + ind_as_interest, 2)

            us_gaap_rent = round((payment * term) / term, 2)
            delta = round(ind_as_total - us_gaap_rent, 2)

            total_ind_as_expense += ind_as_total
            total_us_gaap_expense += us_gaap_rent
            total_delta += delta

            jv = f"JV-ASC842-{self.jv_counter:03d}"
            self.jv_counter += 1

            self._record_jv(jv, "ASC 842 Lease Conversion", "5400", "Operating Lease / Rent Expense", us_gaap_rent, 0.0, f"Recognize straight-line rent under ASC 842 for {contract_id}")
            self._record_jv(jv, "ASC 842 Lease Conversion", "5100", "Depreciation & Amortization - ROU Asset", 0.0, ind_as_amort, f"Derecognize Ind AS 116 amortization for {contract_id}")
            self._record_jv(jv, "ASC 842 Lease Conversion", "5200", "Lease Interest Expense", 0.0, ind_as_interest, f"Derecognize Ind AS 116 financing interest for {contract_id}")
            self._record_jv(jv, "ASC 842 Lease Conversion", "1505", "Accumulated Amortization - ROU Asset", delta, 0.0, f"ROU asset balance adjustment under ASC 842 for {contract_id}")

        return {
            "IndAS_Total_Expense": total_ind_as_expense,
            "US_GAAP_Total_Expense": total_us_gaap_expense,
            "Net_PL_Benefit_to_US_GAAP": total_delta,
        }

    def process_ecl_adjustments(self, ind_as_rate=0.0189, cecl_lifetime_rate=0.0350) -> Dict[str, float]:
        receivables_row = self.tb_df[self.tb_df["Account_Code"].astype(str).str.strip() == "1100"]

        if receivables_row.empty:
            raise ValueError("Gross Trade Receivables (Account 1100) not found in Trial Balance.")

        gross_receivables = float(receivables_row["IndAS_Balance"].values[0])

        current_reserve = round(gross_receivables * ind_as_rate, 2)
        required_reserve = round(gross_receivables * cecl_lifetime_rate, 2)
        incremental_provision = round(required_reserve - current_reserve, 2)

        jv = f"JV-ASC326-{self.jv_counter:03d}"
        self.jv_counter += 1

        self._record_jv(jv, "ASC 326 CECL Conversion", "5300", "Provision for Credit Losses", incremental_provision, 0.0, f"Incremental CECL Lifetime reserve ({cecl_lifetime_rate*100:.2f}% vs {ind_as_rate*100:.2f}%)")
        self._record_jv(jv, "ASC 326 CECL Conversion", "1105", "Allowance for Credit Losses (Contra-Asset)", 0.0, incremental_provision, "Step-up reserve balance to satisfy ASC 326")

        return {
            "Gross_Receivables": gross_receivables,
            "IndAS_109_Reserve": current_reserve,
            "ASC_326_CECL_Reserve": required_reserve,
            "Incremental_Provision": incremental_provision,
        }

    def generate_reconciliation_jvs(self, output_dir="outputs") -> pd.DataFrame:
        os.makedirs(output_dir, exist_ok=True)
        jvs_df = pd.DataFrame(self.journal_vouchers)
        total_debits = round(jvs_df["Debit_USD"].sum(), 2)
        total_credits = round(jvs_df["Credit_USD"].sum(), 2)

        if round(abs(total_debits - total_credits), 2) != 0.0:
            raise AssertionError(f"Out of balance! Debits: {total_debits}, Credits: {total_credits}")

        output_path = os.path.join(output_dir, "GAAP_Conversion_Journal_Vouchers.csv")
        jvs_df.to_csv(output_path, index=False)
        return jvs_df
