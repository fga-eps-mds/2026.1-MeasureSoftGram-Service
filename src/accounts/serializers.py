from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from accounts.models import CustomUser


class AccountsCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'password')

    def save(self):
        password = self.validated_data['password']
        user = CustomUser.objects.create(**self.validated_data)
        user.set_password(password)
        user.save()
        self.token = Token.objects.create(user=user)
        return self.validated_data

    def to_representation(self, validated_data):
        return {'key': self.token.key}


class AccountsRetrieveSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()
    repos_url = serializers.SerializerMethodField()
    organizations_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'avatar_url',
            'repos_url',
            'organizations_url',
        )

    @property
    def socialaccount(self):
        if self.instance.socialaccount_set.exists():
            return self.instance.socialaccount_set.first()

    def get_avatar_url(self, obj):
        if self.socialaccount:
            return self.socialaccount.extra_data['avatar_url']

    def get_repos_url(self, obj):
        if self.socialaccount:
            return self.socialaccount.extra_data['repos_url']

    def get_organizations_url(self, obj):
        if self.socialaccount:
            return self.socialaccount.extra_data['organizations_url']


class AccountsLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, max_length=150)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get('username') and not attrs.get('email'):
            raise serializers.ValidationError('Username OR email required.')
        if attrs.get('username') and attrs.get('email'):
            raise serializers.ValidationError('ONLY Username OR email.')

        username_or_email = 'email' if attrs.get('email') else 'username'
        kwargs = {username_or_email: attrs[username_or_email]}

        try:
            self.user = CustomUser.objects.get(**kwargs)
        except ObjectDoesNotExist:
            raise serializers.ValidationError('Username or email nonexistent.')

        if not self.user.check_password(attrs['password']):
            raise serializers.ValidationError(
                'Invalid username/email or password'
            )

        return attrs

    def save(self):
        self.token, _ = Token.objects.get_or_create(user=self.user)
        return self.token


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'first_name', 'last_name', 'email')


class APIAcessTokenRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = ('key',)


class GitHubAccessTokenRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = ('key',)
