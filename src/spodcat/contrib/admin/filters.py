from django.contrib import admin


class ArtistSongCountFilter(admin.SimpleListFilter):
    parameter_name = "song_count"
    title = "song count"

    def lookups(self, request, model_admin):
        return [
            ("0", "0"),
            ("1", "1"),
            ("2-10", "2-10"),
            ("10-", "10+"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "0":
            return queryset.filter(song_count=0)
        if self.value() == "1":
            return queryset.filter(song_count=1)
        if self.value() == "2-10":
            return queryset.filter(song_count__gte=2, song_count__lte=10)
        if self.value() == "10-":
            return queryset.filter(song_count__gt=10)
        return queryset
