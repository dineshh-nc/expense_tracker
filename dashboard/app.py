import datetime as dt
from contextlib import contextmanager

import pandas as pd
import requests
import streamlit as st

API = "http://127.0.0.1:8000"
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
PAYMENT_METHODS = ["UPI", "Card", "Cash", "Net banking"]

st.set_page_config(page_title="Expense Tracker", page_icon="💰")
st.title("Expense Tracker")


class SessionExpired(Exception):
    pass


def call(method, path, timeout=10, **kwargs):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    response = requests.request(method, f"{API}{path}", headers=headers, timeout=timeout, **kwargs)
    if response.status_code == 401:
        raise SessionExpired()
    return response


def get(path, **params):
    response = call("GET", path, params=params)
    response.raise_for_status()
    return response.json()


@contextmanager
def backend_errors():
    try:
        yield
    except SessionExpired:
        st.session_state.clear()
        st.session_state["login_notice"] = "Your session expired. Please log in again."
        st.rerun()
    except requests.exceptions.HTTPError as exc:
        st.error(f"The backend returned an error ({exc.response.status_code}). Check the uvicorn terminal.")
        st.stop()
    except requests.exceptions.RequestException:
        st.error("Can't reach the backend. Is uvicorn running?")
        st.stop()


def error_text(response):
    detail = response.json().get("detail") if response.headers.get("content-type", "").startswith("application/json") else None
    if isinstance(detail, str):
        return detail
    return "Please check the email and use a password of at least 8 characters."


def show_login():
    notice = st.session_state.pop("login_notice", None)
    if notice:
        st.warning(notice)

    tab_login, tab_register = st.tabs(["Log in", "Register"])

    with tab_login:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in")
        if submitted:
            try:
                response = requests.post(
                    f"{API}/auth/login",
                    data={"username": email, "password": password},
                    timeout=10,
                )
            except requests.exceptions.RequestException:
                st.error("Can't reach the backend. Is uvicorn running?")
                return
            if response.status_code == 200:
                st.session_state["token"] = response.json()["access_token"]
                st.session_state["email"] = email.strip().lower()
                st.rerun()
            else:
                st.error(error_text(response))

    with tab_register:
        with st.form("register"):
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password (at least 8 characters)", type="password", key="register_password")
            submitted = st.form_submit_button("Create account")
        if submitted:
            try:
                response = requests.post(
                    f"{API}/auth/register",
                    json={"email": email, "password": password},
                    timeout=10,
                )
            except requests.exceptions.RequestException:
                st.error("Can't reach the backend. Is uvicorn running?")
                return
            if response.status_code == 201:
                st.success("Account created. Now open the Log in tab.")
            else:
                st.error(error_text(response))


if "token" not in st.session_state:
    show_login()
    st.stop()

st.sidebar.write(f"Logged in as {st.session_state['email']}")
if st.sidebar.button("Log out"):
    st.session_state.clear()
    st.rerun()

today = dt.date.today()
year = st.sidebar.number_input("Year", min_value=2020, max_value=2100, value=today.year)
month_name = st.sidebar.selectbox("Month", MONTHS, index=today.month - 1)
month = f"{year}-{MONTHS.index(month_name) + 1:02d}"

with backend_errors():
    categories = get("/categories")

tab_overview, tab_payments, tab_add, tab_import = st.tabs(
    ["Overview", "Payments", "Add payment", "Import CSV"]
)

# The form is handled first, so a new payment shows up in the other tabs straight away.
with tab_add:
    if not categories:
        st.info("Add a category first (POST /categories on the /docs page).")
    else:
        with st.form("add_payment", clear_on_submit=True):
            amount = st.number_input("Amount (₹)", min_value=0.01, step=10.0, format="%.2f")
            date = st.date_input("Date", value=today)
            category_name = st.selectbox("Category", [c["name"] for c in categories])
            description = st.text_input("Description")
            method = st.selectbox("Payment method", PAYMENT_METHODS)
            submitted = st.form_submit_button("Save payment")

        if submitted:
            category_id = next(c["id"] for c in categories if c["name"] == category_name)
            with backend_errors():
                response = call(
                    "POST",
                    "/transactions",
                    json={
                        "amount": round(amount, 2),
                        "date": date.isoformat(),
                        "description": description or None,
                        "payment_method": method,
                        "category_id": category_id,
                    },
                )
            if response.status_code == 201:
                st.session_state["table_version"] = st.session_state.get("table_version", 0) + 1
                st.success(f"Payment saved on {date:%d %b %Y}. Pick that month in the sidebar to see it.")
            else:
                st.error(f"Could not save: {response.text}")

with backend_errors():
    report = get("/reports/monthly", month=month)
    compare = get("/reports/compare", month=month)
    transactions = get("/transactions", month=month)

with tab_overview:
    st.subheader(f"{month_name} {year}")

    col1, col2 = st.columns(2)
    percent = compare["percent_change"]
    col1.metric(
        "Total spent",
        f"₹{float(report['total']):,.2f}",
        delta=f"{percent}% vs last month" if percent is not None else None,
        delta_color="inverse",  # spending going up shows in red
    )
    col2.metric("Payments", report["payment_count"])

    if report["by_category"]:
        df = pd.DataFrame(report["by_category"])
        df["total"] = df["total"].astype(float)
        st.subheader("Spending by category")
        st.bar_chart(df.set_index("category")["total"])
        st.dataframe(
            df.rename(columns={"category": "Category", "total": "Total (₹)",
                               "count": "Payments", "percent": "% of total"}),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No payments in this month yet.")

with tab_payments:
    st.subheader(f"Payments in {month_name} {year}")

    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)

    if transactions:
        names = {c["id"]: c["name"] for c in categories}
        table = pd.DataFrame(transactions)
        table["Category"] = table["category_id"].map(names)
        table["amount"] = table["amount"].astype(float)
        table = table[["date", "description", "Category", "amount", "payment_method"]]
        table.columns = ["Date", "Description", "Category", "Amount (₹)", "Method"]

        st.caption("Tick the box at the left of a row to select it, then click Delete.")
        event = st.dataframe(
            table,
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="multi-row",
            key=f"payments_table_{month}_{st.session_state.get('table_version', 0)}",
        )
        selected = event.selection.rows

        if selected:
            if st.button(f"Delete {len(selected)} selected payment(s)", type="primary"):
                failed = 0
                with backend_errors():
                    for position in selected:
                        transaction_id = transactions[position]["id"]
                        result = call("DELETE", f"/transactions/{transaction_id}")
                        if result.status_code != 204:
                            failed += 1
                if failed:
                    st.session_state["flash"] = f"{failed} payment(s) could not be deleted."
                else:
                    st.session_state["flash"] = f"Deleted {len(selected)} payment(s)."
                st.session_state["table_version"] = st.session_state.get("table_version", 0) + 1
                st.rerun()
    else:
        st.info("No payments in this month yet.")

with tab_import:
    st.subheader("Import payments from a CSV file")
    st.caption("The file needs the columns: date, description, amount. payment_method is optional.")

    result = st.session_state.pop("import_result", None)
    if result:
        st.success(
            f"Imported {result['imported']} payment(s). "
            f"Skipped {result['skipped_duplicates']} duplicate(s)."
        )
        if result["errors"]:
            st.warning(f"{len(result['errors'])} row(s) could not be imported:")
            st.dataframe(pd.DataFrame(result["errors"]), hide_index=True, use_container_width=True)

    uploaded = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded is not None and st.button("Import this file", type="primary"):
        with backend_errors():
            response = call(
                "POST",
                "/import/csv",
                timeout=30,
                files={"file": (uploaded.name, uploaded.getvalue(), "text/csv")},
            )
        if response.status_code == 200:
            st.session_state["import_result"] = response.json()
            st.session_state["table_version"] = st.session_state.get("table_version", 0) + 1
            st.rerun()
        else:
            st.error(response.json().get("detail", response.text))