"""USSD log parsing utilities.

The USSD logs returned by RouterOS are plain text messages
containing data usage, validity and other account information. This
module provides functions to extract structured information from
these messages using regular expressions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional


# Regex patterns for extracting data amount and unit. We allow both
# GB and MB (case insensitive) and capture decimal commas/dots. The
# first group captures the number, the second the unit.
_DATA_PATTERN = re.compile(r"(\d+[\.,]?\d*)\s*(GB|MB)", re.IGNORECASE)

# Regex pattern for extracting validity in days. Accepts "dias"
# (Spanish for days) with optional accented i. It captures the
# integer number of days.
_VALIDITY_PATTERN = re.compile(r"(\d+)\s*d[ií]as", re.IGNORECASE)

# Pattern to detect low balance phrases. We match phrases like
# "saldo insuficiente" regardless of accents or case.
_LOW_BALANCE_PATTERN = re.compile(r"saldo\s+insuficiente", re.IGNORECASE)


def _normalize_number(num_str: str) -> float:
    """Convert a number string into a float.

    Commas are replaced with dots before conversion. Returns 0.0 if
    conversion fails.
    """
    s = num_str.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_ussd_logs(log_entries: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract structured information from a sequence of log entries.

    Args:
        log_entries: An iterable of log dictionaries as returned by
            the MikroTik REST API. Each entry should contain a
            ``message`` key with a string value.

    Returns:
        A dictionary with keys ``data_gb`` (float), ``valid_days`` (int)
        and ``low_balance`` (bool). If no relevant information is found,
        the values will be None or False.
    """
    data_gb: Optional[float] = None
    valid_days: Optional[int] = None
    low_balance = False

    # Examine messages in reverse chronological order so we act on
    # the most recent relevant message.
    for entry in reversed(list(log_entries)):
        message = entry.get("message") or ""
        if not isinstance(message, str):
            continue
        text = message.lower()
        # Detect low balance first; it's important even if there is no data.
        if _LOW_BALANCE_PATTERN.search(text):
            low_balance = True
        # Attempt to extract data amount and unit.
        data_match = _DATA_PATTERN.search(text)
        if data_match and data_gb is None:
            number_str, unit = data_match.groups()
            amount = _normalize_number(number_str)
            if unit.lower() == "mb":
                amount = amount / 1024.0
            data_gb = round(amount, 2)
        # Attempt to extract validity.
        validity_match = _VALIDITY_PATTERN.search(text)
        if validity_match and valid_days is None:
            days_str = validity_match.group(1)
            try:
                valid_days = int(days_str)
            except ValueError:
                pass
        # If we have extracted all information, break.
        if data_gb is not None and valid_days is not None and low_balance:
            break

    return {
        "data_gb": data_gb,
        "valid_days": valid_days,
        "low_balance": low_balance,
    }
