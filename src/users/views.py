from rest_framework_json_api import views

from users import serializers
from users.models import User


class UserViewSet(views.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
