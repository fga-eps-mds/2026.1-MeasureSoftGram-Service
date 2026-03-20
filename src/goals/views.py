from rest_framework import mixins, status, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.reverse import reverse

from goals.models import Goal
from goals.serializers import (
    GoalSerializer,
    AllGoalsSerializer,
    ReleasesSerializer,
)
from organizations.models import Product
from accounts.models import CustomUser


class GoalModelViewSetMixin(
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Goal.objects.all()
    serializer_args = {}

    def this_product_does_not_have_a_goal_reponse(self, product):
        create_a_new_goal_url = reverse(
            'create-goal-list',
            kwargs={
                'product_pk': product.id,
                'organization_pk': product.organization.id,
            },
            request=self.request,
        )

        data = {
            'detail': 'This product does not have a goal.',
            'actions': {
                'create a new goal': create_a_new_goal_url,
            },
        }

        return Response(data, status=status.HTTP_404_NOT_FOUND)

    def list(self, request, *args, **kwargs):
        product = get_object_or_404(
            Product,
            pk=kwargs['product_pk'],
            organization_id=kwargs['organization_pk'],
        )
        latest_goal = self.get_goals(product)

        if not latest_goal:
            return self.this_product_does_not_have_a_goal_reponse(product)

        serializer = self.serializer_class(latest_goal, **self.serializer_args)
        return Response(serializer.data, status.HTTP_200_OK)


class CurrentGoalModelViewSet(GoalModelViewSetMixin):
    serializer_class = GoalSerializer

    def get_goals(self, product):
        return Goal.objects.filter(product=product).first()


class CompareGoalsModelViewSet(GoalModelViewSetMixin):
    serializer_class = AllGoalsSerializer
    serializer_args = {'many': True}

    def get_goals(self, product):
        release_id = self.request.query_params.get('release_id', None)
        if release_id:
            return Goal.objects.filter(id=release_id)
        return Goal.objects.filter(product=product)


class CreateGoalModelViewSet(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = GoalSerializer
    queryset = Goal.objects.all()

    def get_user(self):
        queryset = CustomUser.objects.all()
        return get_object_or_404(queryset, username=self.request.user)

    def get_product(self):
        return get_object_or_404(
            Product,
            id=self.kwargs['product_pk'],
            organization_id=self.kwargs['organization_pk'],
        )

    def perform_create(self, serializer):
        product = self.get_product()
        created_by = self.get_user()
        serializer.save(product=product, created_by=created_by)
