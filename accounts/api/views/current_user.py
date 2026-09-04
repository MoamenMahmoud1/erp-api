from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


User = get_user_model()


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        # JWT authentication intentionally returns a stateless TokenUser.
        # This endpoint genuinely needs user profile fields, so perform one
        # explicit User query here instead of making authentication stateful.
        user = User.objects.get(pk=request.user.pk)
        return Response(
            {
                "id": user.pk,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
            }
        )
