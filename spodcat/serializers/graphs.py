from rest_framework import serializers


class GraphDataPointSerializer(serializers.Serializer):
    x = serializers.IntegerField()
    y = serializers.FloatField()


class GraphDatasetSerializer(serializers.Serializer):
    label = serializers.CharField()  # pyright: ignore[reportAssignmentType]
    data = GraphDataPointSerializer(many=True)  # pyright: ignore[reportAssignmentType]


class GraphSerializer(serializers.Serializer):
    datasets = GraphDatasetSerializer(many=True)
    earliestDate = serializers.DateField()
