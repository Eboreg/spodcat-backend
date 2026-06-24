from django.utils.log import AdminEmailHandler as BaseAdminEmailHandler


class AdminEmailHandler(BaseAdminEmailHandler):
    _record_name: str

    def emit(self, record):
        self._record_name = record.name
        super().emit(record)

    def format_subject(self, subject):
        subject = super().format_subject(subject)

        if hasattr(self, "_record_name"):
            return f"[{self._record_name}] {subject}"

        return subject
