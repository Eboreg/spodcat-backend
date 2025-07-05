from rest_framework import serializers


# pylint: disable=abstract-method
class ChartDataPointSerializer(serializers.Serializer):
    x = serializers.IntegerField()
    y = serializers.FloatField()


# pylint: disable=abstract-method
class ChartDatasetSerializer(serializers.Serializer):
    label = serializers.CharField()
    data = ChartDataPointSerializer(many=True)


# pylint: disable=abstract-method
class ChartSerializer(serializers.Serializer):
    datasets = ChartDatasetSerializer(many=True)
