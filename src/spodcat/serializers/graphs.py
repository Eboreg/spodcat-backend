from rest_framework import serializers


# pylint: disable=abstract-method
class GraphDataPointSerializer(serializers.Serializer):
    x = serializers.IntegerField()
    y = serializers.FloatField()


# pylint: disable=abstract-method
class GraphDatasetSerializer(serializers.Serializer):
    label = serializers.CharField() # type: ignore
    data = GraphDataPointSerializer(many=True) # type: ignore


# pylint: disable=abstract-method
class GraphSerializer(serializers.Serializer):
    datasets = GraphDatasetSerializer(many=True)
