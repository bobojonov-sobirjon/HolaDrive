from rest_framework import serializers
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from ..models import CustomUser, VerificationCode, PasswordResetToken, UserDeviceToken


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
    invitation_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=20,
        help_text="Optional invitation code to use when registering"
    )
    device_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Push notification device token",
    )
    device_type = serializers.ChoiceField(
        write_only=True,
        required=False,
        choices=UserDeviceToken.DeviceType.choices,
        help_text="Device type for push notifications (android, ios, web)",
    )

    class Meta:
        model = CustomUser
        fields = (
            'full_name',
            'email',
            'password',
            'groups',
            'invitation_code',
            'device_token',
            'device_type',
        )
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
        # Remove non-model fields
        invitation_code = validated_data.pop('invitation_code', None)
        device_token = validated_data.pop('device_token', '').strip() if 'device_token' in validated_data else ''
        device_type = validated_data.pop('device_type', None)
        
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

        # Store device token if provided
        if device_token and device_type:
            UserDeviceToken.upsert_token(user=user, token=device_token, mobile=device_type)
        
        # invitation_code is processed in view layer
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
    Serializer for user login.
    - Phone login: only phone_number (and optional device_token, device_type). No password. Verification code will be sent.
    - Email login: email + password required.
    """
    email = serializers.EmailField(required=False, allow_blank=True, help_text="Email address (required for email login)")
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=15, help_text="Phone number (for phone login, no password needed)")
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        style={'input_type': 'password'},
        help_text="User password (required only when logging in with email)"
    )
    device_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Push notification device token",
    )
    device_type = serializers.ChoiceField(
        write_only=True,
        required=False,
        choices=UserDeviceToken.DeviceType.choices,
        help_text="Device type for push notifications (android, ios, web)",
    )

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        phone_number = (attrs.get('phone_number') or '').strip()
        password = attrs.get('password') or ''

        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required.")

        if email and phone_number:
            raise serializers.ValidationError("Provide either email or phone number, not both.")

        user = None
        if phone_number:
            # Phone login: password is NOT required. Just check user exists.
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"phone_number": ["User with this phone number does not exist."]})
            attrs['user'] = user
            attrs['phone_number'] = phone_number
            return attrs

        # Email login: password IS required
        if not password:
            raise serializers.ValidationError({"password": ["This field is required when logging in with email."]})
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")
        attrs['user'] = user
        attrs['email'] = email
        return attrs


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
    Serializer for password reset confirmation.
    No token: user is identified by email or phone. Reset is allowed only if they
    previously verified via verify-reset-code (which creates a PasswordResetToken for the user).
    """
    email = serializers.EmailField(required=False, allow_blank=True, help_text="Email (to identify whose password to reset)")
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=15, help_text="Phone number (to identify whose password to reset)")
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
        email = (attrs.get('email') or '').strip()
        phone_number = (attrs.get('phone_number') or '').strip()
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')

        if not email and not phone_number:
            raise serializers.ValidationError("Either email or phone number is required to identify the user.")

        if email and phone_number:
            raise serializers.ValidationError("Provide either email or phone number, not both.")

        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        user = None
        if email:
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"email": "User with this email does not exist."})
        else:
            try:
                user = CustomUser.objects.get(phone_number=phone_number)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"phone_number": "User with this phone number does not exist."})

        # Allow reset only if user has a valid (unused, not expired) PasswordResetToken from verify-reset-code
        reset_token = (
            PasswordResetToken.objects.filter(user=user, is_used=False)
            .order_by('-created_at')
            .first()
        )
        if not reset_token or not reset_token.is_valid():
            raise serializers.ValidationError(
                {"email": "Please verify the reset code first (POST verify-reset-code) before changing password."}
                if email else
                {"phone_number": "Please verify the reset code first (POST verify-reset-code) before changing password."}
            )

        attrs['user'] = user
        attrs['reset_token'] = reset_token
        return attrs

