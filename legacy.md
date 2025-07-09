# Unused code, saved here because it seems like a waste to throw it away

## Apply audio gain

From EpisodeAdmin:

```python
    def apply_gain(self, instance: Episode, audio: AudioSegment, stem: str, tags: Any, save: bool = True) -> bool:
        max_dbfs = audio.max_dBFS

        if max_dbfs < 0:
            dbfs = audio.dBFS
            if dbfs < -14:
                gain = min(-max_dbfs, -dbfs - 14)
                logger.info("Applying %f dBFS gain to %s", gain, instance)
                audio = audio.apply_gain(gain)

                try:
                    new_file = audio.export(stem + ".mp3", format="mp3", bitrate="192k", tags=tags)
                    assert isinstance(new_file, IO)
                    delete_storage_file(instance.audio_file)
                    instance.audio_file.save(name=stem + ".mp3", content=File(new_file), save=False)
                    new_file.seek(0)
                    instance.audio_content_type = "audio/mpeg"
                    instance.audio_file_length = len(new_file.read())
                finally:
                    assert isinstance(new_file, IO)
                    new_file.close()

                if save:
                    instance.save(update_fields=["audio_file", "audio_content_type", "audio_file_length"])

                return True

        return False

    def handle_audio_file_async(self, instance: Episode, temp_file: tempfile._TemporaryFileWrapper):
        logger.info("handle_audio_file_async starting for %s, temp_file=%s", instance, temp_file)

        try:
            instance.get_dbfs_and_duration(temp_file=temp_file)
            temp_stem, _ = os.path.splitext(temp_file.name)
            if self.apply_gain(instance=instance, audio=audio, stem=temp_stem, tags=info.get("TAG"), save=False):
                update_fields.extend(["audio_file", "audio_content_type", "audio_file_length"])
            logger.info("handle_audio_file_async finished for %s", instance)
        except Exception as e:
            logger.error("handle_audio_file_async error", exc_info=e)
```

## Get play time from log

From PodcastEpisodeAudioRequestLogQuerySet:

```python
    def get_play_time_query(self, **filters):
        # Not used, keeping it just in case
        from django.db import connections

        connection = connections[self.db]
        if connection.vendor == "postgresql":
            play_time = Cast(Concat(Sum(F("play_time")), V(" seconds")), DurationField())
        else:
            play_time = Cast(Sum(F("play_time")) * 1_000_000, DurationField())

        return (
            self
            .filter(**filters)
            .order_by()
            .values(*filters.keys())
            .with_play_time_alias()
            .annotate(play_time=play_time)
            .values("play_time")
        )
```
