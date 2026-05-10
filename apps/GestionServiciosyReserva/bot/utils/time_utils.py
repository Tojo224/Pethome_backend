from datetime import datetime, time, date


class ChatbotTimeUtils:
    @staticmethod
    def normalize_time(value):
        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        if len(value) == 2 and value.isdigit():
            return f"{value}:00:00"

        if len(value) == 1 and value.isdigit():
            return f"0{value}:00:00"

        if len(value) == 5:
            return f"{value}:00"

        return value

    @staticmethod
    def to_time(value):
        value = ChatbotTimeUtils.normalize_time(value)

        if not value:
            return None

        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                pass

        return None

    @staticmethod
    def to_date(value):
        if value is None:
            return None

        if isinstance(value, date):
            return value

        value = str(value).strip()

        if not value:
            return None

        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def time_to_string(value):
        if value is None:
            return None

        if isinstance(value, time):
            return value.strftime("%H:%M:%S")

        return ChatbotTimeUtils.normalize_time(value)