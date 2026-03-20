from rest_framework import serializers

from releases.models import Release
from goals.models import Goal
from accounts.models import CustomUser
from organizations.models import Product


class ReleaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Release
        fields = (
            'id',
            'release_name',
            'start_at',
            'end_at',
            'created_by',
            'product',
            'goal',
            'description',
        )
        read_only_fields = ('created_by', 'product')

    def verify_fields_releases(
        self, releases, date_start, date_end, release_name
    ):
        if date_start > date_end:
            raise serializers.ValidationError(
                {'message': 'The start date must be less than the end date'}
            )

        for release in releases:
            if date_start >= release.start_at and date_start <= release.end_at:
                raise serializers.ValidationError(
                    {
                        'message': 'The start date must be greater than the start date of the previous release'
                    }
                )

            if release_name == release.release_name:
                raise serializers.ValidationError(
                    {'message': 'The release name must be unique'}
                )

    def create(self, validated_data):

        release = Release.objects.all().filter(
            product=Product.objects.get(
                id=self.context['view'].kwargs['product_pk']
            )
        )
        self.verify_fields_releases(
            release,
            validated_data['start_at'],
            validated_data['end_at'],
            validated_data['release_name'],
        )

        validated_data['created_by'] = CustomUser.objects.get(
            id=self.context['view'].request.user.id
        )
        validated_data['product'] = Product.objects.get(
            id=self.context['view'].kwargs['product_pk']
        )
        return Release.objects.create(**validated_data)

    def update(self, validated_data):
        release = Release.objects.all().filter(
            product=Product.objects.get(
                id=self.context['view'].kwargs['product_pk']
            )
        )
        self.verify_fields_releases(
            release,
            validated_data['start_at'],
            validated_data['end_at'],
            validated_data['release_name'],
        )
        return Release.objects.update(**validated_data)


class CheckReleaseSerializer(serializers.Serializer):
    nome = serializers.CharField(max_length=255)
    dt_inicial = serializers.DateField()
    dt_final = serializers.DateField()

    def validate(self, data):
        if data['dt_inicial'] > data['dt_final']:
            raise serializers.ValidationError(
                {'message': 'The start date must be less than the end date'}
            )

        return data


class ReleaseAllSerializer(serializers.ModelSerializer):
    class Meta:
        model = Release
        fields = '__all__'


class ReleaseAccomplishedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = 'data'
