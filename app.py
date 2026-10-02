import os
import tempfile
import pandas as pd
import streamlit as st
from src.modules.conversion_engine import GAAPConversionEngine

st.set_page_config(
    page_title="Dual-GAAP Reconciliation Engine",
    page_icon="⚖️",
    layout="wide",
)

st.title("⚖️ Dual-GAAP Reconciliation Engine")
st.caption("Technical Accounting Automation: Ind AS (IFRS-converged) ⇌ US GAAP (ASC 842 & ASC 326)")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("📁 Data Source")
data_mode = st.sidebar.radio(
    "Choose Input Mode:",
    ("Use Built-in Sample Data", "Upload Custom CSVs"),
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ CECL Loss Rate Assumptions")
ind_as_ecl_pct = st.sidebar.number_input(
    "Ind AS 109 12-Month ECL Rate (%)",
    min_value=0.0,
    max_value=100.0,
    value=1.89,
    step=0.01,
)
us_gaap_cecl_pct = st.sidebar.number_input(
    "ASC 326 Day-1 Lifetime CECL Rate (%)",
    min_value=0.0,
    max_value=100.0,
    value=3.50,
    step=0.01,
)

# Convert percentage to decimal
ind_as_rate = ind_as_ecl_pct / 100.0
cecl_rate = us_gaap_cecl_pct / 100.0

tb_path = None
lease_path = None
temp_dir = tempfile.gettempdir()

if data_mode == "Use Built-in Sample Data":
    tb_path = os.path.join("data", "sample_trial_balance.csv")
    lease_path = os.path.join("data", "lease_contracts.csv")
    st.info("Using default repo sample files (`data/sample_trial_balance.csv` & `data/lease_contracts.csv`).")

else:
    st.subheader("Upload Statutory Trial Balance & Lease Portfolio")
    col_u1, col_u2 = st.columns(2)

    with col_u1:
        uploaded_tb = st.file_uploader("Upload Trial Balance (CSV)", type=["csv"])
        if uploaded_tb:
            tb_path = os.path.join(temp_dir, "custom_tb.csv")
            with open(tb_path, "wb") as f:
                f.write(uploaded_tb.getbuffer())
            st.success("Trial Balance loaded.")

    with col_u2:
        uploaded_lease = st.file_uploader("Upload Lease Register (CSV)", type=["csv"])
        if uploaded_lease:
            lease_path = os.path.join(temp_dir, "custom_lease.csv")
            with open(lease_path, "wb") as f:
                f.write(uploaded_lease.getbuffer())
            st.success("Lease Register loaded.")

# --- EXECUTION BUTTON ---
st.markdown("---")
run_clicked = st.button("🚀 Run Dual-GAAP Reconciliation Pipeline", type="primary")

if run_clicked:
    if not tb_path or not lease_path:
        st.error("Please ensure both Trial Balance and Lease Register files are uploaded before running.")
    else:
        try:
            # Initialize engine
            engine = GAAPConversionEngine(
                trial_balance_path=tb_path,
                lease_contracts_path=lease_path,
            )

            # Process Modules
            lease_metrics = engine.process_lease_adjustments()
            ecl_metrics = engine.process_ecl_adjustments(
                ind_as_rate=ind_as_rate,
                cecl_lifetime_rate=cecl_rate,
            )
            jv_df = engine.generate_reconciliation_jvs()

            # --- DISPLAY KEY FINANCIAL METRICS ---
            st.subheader("1. Executive Variance Summary")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(
                label="Ind AS 116 Lease Cost",
                value=f"${lease_metrics['IndAS_Total_Expense']:,.2f}",
            )
            m2.metric(
                label="US GAAP ASC 842 Rent",
                value=f"${lease_metrics['US_GAAP_Total_Expense']:,.2f}",
                delta=f"+${lease_metrics['Net_PL_Benefit_to_US_GAAP']:,.2f} Pre-Tax Benefit",
            )
            m3.metric(
                label="Ind AS 109 ECL Reserve",
                value=f"${ecl_metrics['IndAS_109_Reserve']:,.2f}",
            )
            m4.metric(
                label="ASC 326 CECL Provision Required",
                value=f"${ecl_metrics['Incremental_Provision']:,.2f}",
                delta=f"-${ecl_metrics['Incremental_Provision']:,.2f} Pre-Tax Hit",
                delta_color="inverse",
            )

            # --- AUDIT BALANCING CONTROLS ---
            st.markdown("---")
            st.subheader("2. Audit Trail & Balanced Conversion Journal Vouchers")

            total_debits = jv_df["Debit_USD"].sum()
            total_credits = jv_df["Credit_USD"].sum()
            imbalance = abs(total_debits - total_credits)

            c_ctrl1, c_ctrl2, c_ctrl3 = st.columns(3)
            c_ctrl1.metric("Total Adjustment Debits", f"${total_debits:,.2f}")
            c_ctrl2.metric("Total Adjustment Credits", f"${total_credits:,.2f}")
            if imbalance == 0.0:
                c_ctrl3.success("✅ Audit Check: BALANCED (Debits == Credits)")
            else:
                c_ctrl3.error(f"❌ Imbalance: ${imbalance:,.2f}")

            # Display Ledger Entries
            display_cols = ["JV_ID", "Adjustment_Category", "Account_Code", "Account_Name", "Debit_USD", "Credit_USD", "Narration"]
            st.dataframe(jv_df[display_cols], use_container_width=True)

            # Download CSV
            csv_data = jv_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Conversion Journal Vouchers (CSV)",
                data=csv_data,
                file_name="GAAP_Conversion_Journal_Vouchers.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"Execution Error: {str(e)}")
