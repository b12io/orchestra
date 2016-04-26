from orchestra.tests.helpers import OrchestraTestCase
from orchestra.utils.models import ChoicesEnum


class ModelUtilsTests(OrchestraTestCase):

    def test_choices_enum(self):
        class TestEnum(ChoicesEnum):
            val0 = 'desc0'
            val1 = 'desc1'
            val2 = 'desc2'

        self.assertEqual(TestEnum.val0.description, 'desc0')
        self.assertEqual(TestEnum.val1.description, 'desc1')
        self.assertEqual(TestEnum.val2.description, 'desc2')
        self.assertEqual(TestEnum.val0.value, 0)
        self.assertEqual(TestEnum.val1.value, 1)
        self.assertEqual(TestEnum.val2.value, 2)
        self.assertEqual(TestEnum.val0.name, 'val0')
        self.assertEqual(TestEnum.val1.name, 'val1')
        self.assertEqual(TestEnum.val2.name, 'val2')

        expected_choices = [
            (0, 'desc0'),
            (1, 'desc1'),
            (2, 'desc2'),
        ]
        self.assertEqual(TestEnum.choices(), expected_choices)

        expected_data = {
            'val0': {
                'description': 'desc0',
                'value': 0
            },
            'val1': {
                'description': 'desc1',
                'value': 1
            },
            'val2': {
                'description': 'desc2',
                'value': 2
            },
        }
        self.assertEqual(TestEnum.serialize(), expected_data)
