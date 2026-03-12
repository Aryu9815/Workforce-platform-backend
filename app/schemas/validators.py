# app/utils/validators.py

import re
from datetime import date, datetime


def _normalize_whitespace(value: str) -> str:
    value = value.strip()
    return re.sub(r"\s+", " ", value)


def validate_name_field(
    value: str | None,
    field: str = "name",
    max_length: int = 100,
    is_optional: bool = False,
    only_letters: bool = False,
):
    if value is None or value == "":
        if is_optional:
            return None
        raise ValueError(f"{field} is required")

    value = _normalize_whitespace(str(value))

    if not re.fullmatch(r"[A-Za-z0-9 ]+", value) and not only_letters:
        raise ValueError(f"{field} can only contain letters, numbers, and spaces")
    
    if only_letters and not re.fullmatch(r"[A-Za-z ]+", value):
        raise ValueError(f"{field} can only contain letters and spaces")
    
    if len(value) > max_length:
        raise ValueError(f"{field} cannot exceed {max_length} characters")

    return value


def validate_description(
    value: str | None,
    max_length: int = 500,
    is_optional: bool = True,
    field: str = "description",
):
    if value is None or value == "":
        if is_optional:
            return None
        raise ValueError(f"{field} is required")

    value = _normalize_whitespace(str(value))

    if max_length and len(value) > max_length:
        raise ValueError(f"{field} cannot exceed {max_length} characters")

    return value


def validate_optional_str(value: str | None, max_length: int | None = None, field: str = "value"):
    if value is None or value == "":
        return None

    value = _normalize_whitespace(str(value))

    if max_length and len(value) > max_length:
        raise ValueError(f"{field} cannot exceed {max_length} characters")

    return value


def validate_code_field(
    value: str | None,
    field: str = "code",
    max_length: int = 20,
    is_optional: bool = False,
):
    if value is None or value == "":
        if is_optional:
            return None
        raise ValueError(f"{field} is required")

    value = str(value).strip().upper()

    pattern = r"^[A-Z0-9\-\_\#\@]+$"
    if not re.fullmatch(pattern, value):
        raise ValueError(f"{field} can only contain A-Z, 0-9, '-', '_', '#', '@'")

    if len(value) > max_length:
        raise ValueError(f"{field} cannot exceed {max_length} characters")

    return value


def validate_positive_number(
    value: float | int | None,
    field: str = "value",
    is_optional: bool = False,
    strictly_positive: bool = True,
):
    if value is None:
        if is_optional:
            return None
        raise ValueError(f"{field} is required")

    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number")

    if strictly_positive:
        if num <= 0:
            raise ValueError(f"{field} must be greater than 0")
    else:
        if num < 0:
            raise ValueError(f"{field} must be a positive number")

    return num

def _parse_datetime(value_str: str, field: str):
    try:
        return datetime.fromisoformat(value_str.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{field} must be a valid ISO datetime (YYYY-MM-DDTHH:MM:SS)")

def _parse_date(value_str: str, field: str):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value_str):
        raise ValueError(f"{field} must be in YYYY-MM-DD format")

    try:
        return datetime.strptime(value_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{field} must be a valid date")
    

def _check_date_limits(result, is_datetime, today, field, allowed_past, allowed_future):
    check_val = result.date() if is_datetime else result

    if not allowed_past and check_val < today:
        raise ValueError(f"{field} cannot be in the past")

    if not allowed_future and check_val > today:
        raise ValueError(f"{field} cannot be in the future")
    
def validate_date_ymd(
    value,
    field: str = "date",
    is_optional: bool = False,
    is_datetime: bool = False,
    allowed_past: bool = True,
    allowed_future: bool = True,
):
    """
    Ensure date inputs are in YYYY-MM-DD format when provided as strings.
    Accepts and returns `datetime.date` objects as-is.
    """
    now = datetime.now()
    today = now.date()

    if value is None or value == "":
        if is_optional:
            return None
        raise ValueError(f"{field} is required")

    result = None

    if isinstance(value, datetime):
        result = value if is_datetime else value.date()

    elif isinstance(value, date):
        result = value if not is_datetime else datetime.combine(value, datetime.min.time())

    else:
        value_str = str(value).strip()
        result = _parse_datetime(value_str, field) if is_datetime else _parse_date(value_str, field)

    _check_date_limits(result, is_datetime, today, field, allowed_past, allowed_future)

    return result
    
    
def validate_phone_number(
    value: str | None,
    field: str = "phone",
    max_length: int = 10,
    min_length: int = 10,
    is_optional: bool = True,
):
    if value is None or value == "":
        if is_optional:
            return None
        raise ValueError(f"{field} is required")

    value = str(value).strip()

    if not re.fullmatch(r"\d+", value):
        raise ValueError(f"{field} can only contain digits")

    if len(value) > max_length:
        raise ValueError(f"{field} cannot exceed {max_length} digits")

    if len(value) < min_length:
        raise ValueError(f"{field} cannot be less than {min_length} digits")
    
    return value