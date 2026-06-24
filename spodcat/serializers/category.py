from rest_framework_json_api import serializers

from spodcat.models import Category


class CategorySerializer(serializers.ModelSerializer[Category]):
    class Meta:
        fields = "__all__"
        model = Category
