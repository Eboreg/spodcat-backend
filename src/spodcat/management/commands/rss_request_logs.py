import itertools

from django.core.management import BaseCommand

from spodcat.models import PodcastRssRequestLog


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--database", default="default")

    def handle(self, *args, **options):
        for path_info, logs in itertools.groupby(
            PodcastRssRequestLog.objects
            .using(options["database"])
            .order_by("path_info", "created"),
            key=lambda l: l.path_info,
        ):
            logs = list(logs)
            requests = len(logs)
            delta = logs[-1].created - logs[0].created
            if not delta:
                continue
            hours = delta.total_seconds() / 60 / 60
            days = hours / 24
            uq_ips = set(l.remote_addr for l in logs)
            referrers = {
                r: [l for l in logs if l.referrer == r]
                for r in set(l.referrer for l in logs) if r
            }

            self.stdout.write(path_info)
            self.stdout.write(f"Total requests: {requests}")
            self.stdout.write(f"Requests/day: {(requests / days):.02f}")
            self.stdout.write(f"Requests/hour: {(requests / hours):.02f}")
            self.stdout.write(f"Unique IPs: {len(uq_ips)}")

            if referrers:
                self.stdout.write("Referrers:")
                for ref, ref_logs in referrers.items():
                    ref_uq_ips = set(l.remote_addr for l in ref_logs)
                    ref_percent = len(ref_logs) / len(logs) * 100
                    self.stdout.write(
                        f" * {ref}: {len(ref_logs)} / {ref_percent:.02f}% ({len(ref_uq_ips)} unique IPs)"
                    )

            self.stdout.write("")
