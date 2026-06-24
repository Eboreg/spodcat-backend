from rest_framework import serializers


# pylint: disable=abstract-method
class GraphDataPointSerializer(serializers.Serializer):
    x = serializers.IntegerField()
    y = serializers.FloatField()


# pylint: disable=abstract-method
class GraphDatasetSerializer(serializers.Serializer):
    label = serializers.CharField()  # pyright: ignore[reportAssignmentType]
    data = GraphDataPointSerializer(many=True)  # pyright: ignore[reportAssignmentType]


# pylint: disable=abstract-method
class GraphSerializer(serializers.Serializer):
    datasets = GraphDatasetSerializer(many=True)
    earliestDate = serializers.DateField()
