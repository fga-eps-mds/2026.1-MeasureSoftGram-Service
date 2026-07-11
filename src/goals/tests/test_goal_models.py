from datetime import date

from django.core.exceptions import ValidationError

from goals.models import Goal
from utils.tests import APITestCaseExpanded


class GoalModelTestCase(APITestCaseExpanded):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.org = self.get_organization(add_user=False)
        self.product = self.get_product(self.org)

    def create_goal(self, data):
        return Goal.objects.create(
            created_at=date.today(),
            created_by=self.user,
            product=self.product,
            data=data,
        )

    def test_validate_goal_returns_true_for_valid_numeric_dict(self):
        self.assertTrue(Goal.validate_goal({"reliability": 53}))
        self.assertTrue(
            Goal.validate_goal({"reliability": 53, "maintainability": 12.5})
        )

    def test_validate_goal_returns_false_for_non_dict(self):
        self.assertFalse(Goal.validate_goal([]))
        self.assertFalse(Goal.validate_goal(None))
        self.assertFalse(Goal.validate_goal("reliability"))

    def test_validate_goal_returns_false_for_empty_dict(self):
        self.assertFalse(Goal.validate_goal({}))

    def test_validate_goal_returns_false_for_non_numeric_value(self):
        self.assertFalse(Goal.validate_goal({"reliability": "alta"}))

    def test_validate_goal_returns_false_for_boolean_value(self):
        self.assertFalse(Goal.validate_goal({"reliability": True}))

    def test_save_raises_for_empty_dict(self):
        with self.assertRaises(ValidationError):
            self.create_goal({})

    def test_save_raises_for_list_data(self):
        with self.assertRaises(ValidationError):
            self.create_goal([])

    def test_save_raises_for_non_numeric_value(self):
        with self.assertRaises(ValidationError):
            self.create_goal({"reliability": "alta"})

    def test_save_persists_valid_goal(self):
        goal = self.create_goal(
            {
                "reliability": 53,
                "maintainability": 53,
                "functional_suitability": 53,
            }
        )
        self.assertIsNotNone(goal.id)
        self.assertEqual(Goal.objects.filter(id=goal.id).count(), 1)


class GoalImmutabilityTestCase(APITestCaseExpanded):
    def setUp(self):
        self.user = self.get_or_create_test_user()
        self.org = self.get_organization(add_user=False)
        self.product = self.get_product(self.org)

    def create_goal(self, data):
        return Goal.objects.create(
            created_at=date.today(),
            created_by=self.user,
            product=self.product,
            data=data,
        )

    def test_queryset_update_raises(self):
        goal = self.create_goal({"reliability": 53})
        with self.assertRaises(ValueError):
            Goal.objects.filter(pk=goal.pk).update(data={"reliability": 99})

    def test_reverse_manager_update_raises(self):
        goal = self.create_goal({"reliability": 53})
        with self.assertRaises(ValueError):
            self.product.goals.filter(pk=goal.pk).update(
                data={"reliability": 99}
            )

    def test_bulk_update_raises(self):
        goal = self.create_goal({"reliability": 53})
        goal.data = {"reliability": 99}
        with self.assertRaises(ValueError):
            Goal.objects.bulk_update([goal], ["data"])

    def test_reads_still_work(self):
        goal = self.create_goal({"reliability": 53})
        self.assertEqual(Goal.objects.filter(pk=goal.pk).first(), goal)
        self.assertEqual(Goal.objects.all().count(), 1)
        self.assertEqual(self.product.goals.count(), 1)
