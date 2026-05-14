import string
import typing


class CustomStringFormatter(string.Formatter):
    def format_field(self, value: typing.Any, format_spec: str) -> str:
        if isinstance(value, tuple) and len(value) == 2:
            actual_value, fallback_value = value
            if actual_value is None:
                return fallback_value

            try:
                return super().format_field(actual_value, format_spec)
            except Exception:
                return fallback_value

        return super().format_field(value, format_spec)
