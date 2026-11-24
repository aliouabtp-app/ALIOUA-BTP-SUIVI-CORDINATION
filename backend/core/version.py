"""مصدر وحيد لإصدار التطبيق، يستعمله endpoint «حول التطبيق» وOpenAPI.
لا يستورد Django عمداً حتى يمكن اختباره منفرداً."""
import re

APP_VERSION = "1.0.0"

_COMMIT_RE = re.compile(r"[0-9a-f]{7,40}")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}(T[0-9:.+\-Z]{1,32})?")


def clean_commit(value):
    """commit مختصر (12 خانة) إن كانت القيمة هاشاً سداسياً صالحاً، وإلا unknown (لا نعكس نصاً غير موثوق)."""
    v = (value or "").strip().lower()
    return v[:12] if _COMMIT_RE.fullmatch(v) else "unknown"


def clean_build_date(value):
    """تاريخ البناء بصيغة ISO إن كان صالحاً، وإلا None."""
    v = (value or "").strip()
    return v if _DATE_RE.fullmatch(v) else None
