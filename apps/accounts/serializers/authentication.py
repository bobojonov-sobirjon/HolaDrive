from rest_framework import serializers
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from ..models import CustomUser, VerificationCode, PasswordResetToken


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    full_name = serializers.CharField(
        write_only=True,
        required=True,
        help_text="User's full name"
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text="User password"
    )
    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(),
        many=True,
        required=False,
        help_text="List of group IDs to assign to the user"
    )

    class Meta:
        model = CustomUser
        fields = ('full_name', 'email', 'password', 'groups')
        extra_kwargs = {
            'email': {'required': True}
        }

    def validate_email(self, value):
        """
        Check if email already exists
        """
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        """
        Create and return a new user instance
        """
        full_name = validated_data.pop('full_name', '')
        groups = validated_data.pop('groups', [])
        password = validated_data.pop('password')
        
        name_parts = full_name.strip().split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        email = validated_data.get('email')
        username = email.split('@')[0] if email else f"user_{CustomUser.objects.count() + 1}"
        
        base_username = username
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = CustomUser.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password,
            **validated_data
        )
        
        if groups:
            user.groups.set(groups)
        
        return user

    def to_representation(self, instance):
        """
        Return user data after registration
        """
        return {
            'id': instance.id,
            'email': instance.email,
            'full_name': instance.get_full_name(),
            'groups': [{'id': group.id, 'name': group.name} for group in instance.groups.all()],
            'username': instance.username,
            'is_verified': instance.is_verified,
            'created_at': instance.created_at
        }


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    email = serializers.EmailField(required=False, help_text="Email address")
    phone_number = serializers.CharField(required=False, max_length=15, help_text="Phone number")
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="User password"
    )
    invitation_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=20,
        help_text="Optional invitation code to use when logging in"
    )

    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required.")

        user = None
        if email:
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError("Invalid email or password.")
        elif phone_number:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError("Invalid phone number or password.")

        if user and user.check_password(password):
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("Invalid email/phone number or password.")


class SendVerificationCodeSerializer(serializers.Serializer):
    """
    Serializer for sending verification code
    """
    email = serializers.EmailField(required=False, help_text="Email address")
    phone_number = serializers.CharField(required=False, max_length=15, help_text="Phone number")

    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')

        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required.")

        # Find user by email or phone number
        user = None
        if email:
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError("User with this email does not exist.")
        elif phone_number:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError("User with this phone number does not exist.")

        attrs['user'] = user
        return attrs


class VerifyCodeSerializer(serializers.Serializer):
    """
    Serializer for verifying code
    """
    email = serializers.EmailField(required=False, help_text="Email address")
    phone_number = serializers.CharField(required=False, max_length=15, help_text="Phone number")
    code = serializers.CharField(
        required=True,
        max_length=4,
        min_length=4,
        help_text="4-digit verification code"
    )
    invitation_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=20,
        help_text="Optional invitation code to use when verifying"
    )

    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        code = attrs.get('code')

        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required.")

        # Find user
        user = None
        if email:
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError("User with this email does not exist.")
        elif phone_number:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError("User with this phone number does not exist.")

        # Find valid verification code with optimized query
        try:
            # Use select_related to fetch user in same query, and only() to select needed fields
            verification_code = VerificationCode.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).select_related('user').only(
                'id', 'user_id', 'code', 'is_used', 'created_at', 'expires_at'
            ).latest('created_at')
            
            if not verification_code.is_valid():
                raise serializers.ValidationError("Verification code has expired.")
            
            attrs['user'] = user
            attrs['verification_code'] = verification_code
            return attrs
        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError("Invalid verification code.")


class ResetPasswordRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request
    """
    email = serializers.EmailField(required=False, help_text="Email address")
    phone_number = serializers.CharField(required=False, max_length=15, help_text="Phone number")

    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')

        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required.")

        user = None
        if email:
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"email": "User with this email does not exist."})
        elif phone_number:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"phone_number": "User with this phone number does not exist."})

        attrs['user'] = user
        return attrs


class VerifyResetCodeSerializer(serializers.Serializer):
    """
    Serializer for verifying reset password code
    """
    email = serializers.EmailField(required=False, help_text="Email address")
    phone_number = serializers.CharField(required=False, max_length=15, help_text="Phone number")
    code = serializers.CharField(
        required=True,
        max_length=4,
        min_length=4,
        help_text="4-digit verification code"
    )

    def validate(self, attrs):
        email = attrs.get('email')
        phone_number = attrs.get('phone_number')
        code = attrs.get('code')

        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required.")

        user = None
        if email:
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"email": "User with this email does not exist."})
        elif phone_number:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"phone_number": "User with this phone number does not exist."})

        try:
            # Optimize query: use select_related and only() for better performance
            verification_code = VerificationCode.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).select_related('user').only(
                'id', 'user_id', 'code', 'is_used', 'created_at', 'expires_at'
            ).latest('created_at')
            
            if not verification_code.is_valid():
                raise serializers.ValidationError({"code": "Verification code has expired."})
            
            attrs['user'] = user
            attrs['verification_code'] = verification_code
            return attrs
        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError({"code": "Invalid verification code."})


class ResetPasswordConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation
    """
    token = serializers.CharField(
        required=True,
        max_length=100,
        help_text="Password reset token"
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
        help_text="New password"
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Confirm new password"
    )

    def validate(self, attrs):
        token = attrs.get('token')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if new_password != confirm_password:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        try:
            # Optimize query: use select_related to fetch user in same query
            reset_token = PasswordResetToken.objects.select_related('user').get(
                token=token,
                is_used=False
            )
            
            if not reset_token.is_valid():
                raise serializers.ValidationError({"token": "Reset token has expired."})
            
            attrs['user'] = reset_token.user
            attrs['reset_token'] = reset_token
            return attrs
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid reset token."})

