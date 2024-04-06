from django.test import TestCase
from .views import combine_records
from collections import OrderedDict

class CombineRecordsTest(TestCase):
    def test_combine_records(self):
        token_tx = {'result': [{'hash': 'hash1', 'value': 'token_value1'}, {'hash': 'hash2', 'value': 'token_value2'}]}
        internal_tx = {'result': [{'hash': 'hash1', 'value': 'internal_value1'}]}
        normal_tx = {'result': [{'hash': 'hash3', 'value': 'normal_value1'}]}



        expected_combined_data = OrderedDict([
            ('hash1', {0: {'hash': 'hash1', 'value': 'token_value1'}, 1: {'hash': 'hash1', 'value': 'internal_value1'}}),
            ('hash2', {0: {'hash': 'hash2', 'value': 'token_value2'}}),
            ('hash3', {0: {'hash': 'hash3', 'value': 'normal_value1'}}),
        ])

        combined_data = combine_records(token_tx, internal_tx, normal_tx)
        
        
        self.assertEqual(combined_data, expected_combined_data, "The combined_data does not match the expected output.")
