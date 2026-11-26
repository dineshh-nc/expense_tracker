import csv
import datetime as dt
import io
from decimal import Decimal, InvalidOperation

DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")
DEFAULT_CATEGORY = "Uncategorized"

# Edit these freely: category -> words to look for in the description
KEYWORDS = {
    "Food": ["swiggy", "zomato", "restaurant", "cafe", "grocery", "groceries", "bigbasket", "blinkit"],
    "Travel": ["uber", "ola", "irctc", "redbus", "metro", "petrol", "fuel"],
    "Bills": ["electricity", "internet", "airtel", "jio", "recharge", "bill"],
    "Shopping": ["amazon", "flipkart", "myntra"],
    "Rent": ["rent"],
}


def guess_category(description: str) -> str:
    text = description.lower()
    for category, words in KEYWORDS.items():
        if any(word in text for word in words):
            return category
    return DEFAULT_CATEGORY


def parse_date(value: str) -> dt.date:
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date '{value}'")


def parse_amount(value: str) -> Decimal:
    cleaned = value.replace(",", "").replace("₹", "").strip()
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"invalid amount '{value}'") from None
    if amount <= 0:
        raise ValueError("amount must be greater than 0")
    return amount.quantize(Decimal("0.01"))


def parse_csv(content: bytes):
    """Returns (valid_rows, errors). Raises ValueError if the file is unusable."""
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    if reader.fieldnames is None:
        raise ValueError("The file is empty")
    reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
    missing = {"date", "description", "amount"} - set(reader.fieldnames)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")

    rows, errors = [], []
    for number, raw in enumerate(reader, start=2):  # line 1 is the header
        try:
            rows.append(
                {
                    "date": parse_date(raw["date"] or ""),
                    "amount": parse_amount(raw["amount"] or ""),
                    "description": (raw["description"] or "").strip()[:255] or None,
                    "payment_method": (raw.get("payment_method") or "").strip()[:30] or None,
                }
            )
        except ValueError as exc:
            errors.append((number, str(exc)))
    return rows, errors