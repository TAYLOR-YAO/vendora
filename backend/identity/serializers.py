from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True, required=True, label="Confirm Password",
    )

    class Meta:
        model = User
        fields = ("username", "email", "full_name", "password1", "password2")
        extra_kwargs = {
            "email": {"required": True},
            "username": {"required": True},
            "full_name": {"required": True},
        }

    def validate(self, attrs):
        if attrs["password1"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            full_name=validated_data["full_name"],
            password=validated_data["password1"],
        )
        return user


class UserDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer for the custom user model for user detail endpoints.
    """
    class Meta:
        model = User
        fields = ("pk", "username", "email", "full_name")
        read_only_fields = ("pk", "email", "username")