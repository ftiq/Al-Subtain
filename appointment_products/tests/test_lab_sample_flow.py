# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from unittest.mock import patch


class TestLabSampleFlow(TransactionCase):
    """Test cases for Lab Sample → Flow → Result Set lifecycle"""

    def setUp(self):
        super().setUp()
        

        self.uom_kg = self.env.ref('uom.product_uom_kgm')
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        

        self.sample_product = self.env['product.template'].create({
            'name': 'Test Sample Product',
            'is_sample_product': True,
            'hole_count': 10,
        })
        

        self.criterion_strength = self.env['lab.test.criterion'].create({
            'name': 'Compressive Strength',
            'code': 'STRENGTH',
            'test_type': 'numeric',
            'is_input_field': True,
            'min_value': 20.0,
            'max_value': 50.0,
            'target_value': 35.0,
            'uom_id': self.uom_kg.id,
            'sequence': 10,
        })
        
        self.criterion_weight = self.env['lab.test.criterion'].create({
            'name': 'Weight',
            'code': 'WEIGHT',
            'test_type': 'numeric',
            'is_input_field': True,
            'min_value': 1.0,
            'max_value': 5.0,
            'uom_id': self.uom_kg.id,
            'sequence': 20,
        })
        

        self.test_template = self.env['lab.test.template'].create({
            'name': 'Test Template',
            'code': 'TT001',
            'state': 'active',
            'criterion_ids': [(6, 0, [self.criterion_strength.id, self.criterion_weight.id])]
        })
        

        self.flow_template = self.env['lab.test.flow.template'].create({
            'name': 'Test Flow Template',
            'line_ids': [(0, 0, {
                'sequence': 10,
                'test_template_id': self.test_template.id,
                'sample_qty': 3,
            })]
        })
        

        self.sample_product.test_flow_template_id = self.flow_template.id
        

        self.project = self.env['project.project'].create({
            'name': 'Test Project'
        })
        
        self.task = self.env['project.task'].create({
            'name': 'Test Task',
            'project_id': self.project.id,
        })

    def test_01_sample_creation_success(self):
        """Test successful sample creation with sequence generation"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'task_id': self.task.id,
            'quantity': 10.0,
        })
        
        self.assertTrue(sample.name)
        self.assertNotEqual(sample.name, 'New')
        self.assertEqual(sample.state, 'draft')
        self.assertEqual(sample.quantity, 10.0)

    def test_02_sample_validation_constraints(self):
        """Test sample validation constraints"""
        with self.assertRaises(ValidationError):
            self.env['lab.sample'].create({
                'product_id': self.sample_product.product_variant_id.id,
                'quantity': 0.0,
            })
        
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'quantity': 5.0,
        })
        
        with self.assertRaises(ValidationError):
            sample.write({
                'collection_date': '2024-01-01',
                'received_date': '2023-12-31 10:00:00',
            })

    def test_03_start_testing_with_flow_template(self):
        """Test starting testing with flow template"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'task_id': self.task.id,
            'quantity': 5.0,
        })
        
        action = sample.action_start_testing()
        
        self.assertEqual(sample.state, 'testing')
        
        self.assertEqual(len(sample.test_flow_ids), 1)
        flow = sample.test_flow_ids[0]
        self.assertEqual(flow.state, 'in_progress')
        self.assertEqual(flow.current_step, 10)
        
        self.assertEqual(len(sample.result_set_ids), 1)
        result_set = sample.result_set_ids[0]
        self.assertEqual(result_set.state, 'draft')
        self.assertEqual(result_set.number_of_samples, 3)
        
        expected_lines = 3 * 2
        self.assertEqual(len(result_set.result_line_ids), expected_lines)

    def test_04_start_testing_without_template(self):
        """Test starting testing without template raises error"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'quantity': 5.0,
        })
        
        self.sample_product.test_flow_template_id = False
        
        with self.assertRaises(UserError):
            sample.action_start_testing()

    def test_05_race_condition_protection(self):
        """Test protection against double-click race conditions"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'task_id': self.task.id,
            'quantity': 5.0,
        })
        
        action1 = sample.action_start_testing()
        self.assertEqual(sample.state, 'testing')
        self.assertEqual(len(sample.test_flow_ids), 1)
        
        action2 = sample.action_start_testing()
        self.assertEqual(len(sample.test_flow_ids), 1)
        
        self.assertEqual(action2['res_model'], 'lab.result.set')

    def test_06_flow_line_sequence_constraint(self):
        """Test unique sequence constraint in flow lines"""
        flow = self.env['lab.test.flow'].create({
            'name': 'Test Flow',
            'sample_id': self.env['lab.sample'].create({
                'product_id': self.sample_product.product_variant_id.id,
                'quantity': 1.0,
            }).id,
            'template_id': self.flow_template.id,
        })
        
        line1 = self.env['lab.test.flow.line'].create({
            'flow_id': flow.id,
            'sequence': 10,
            'test_template_id': self.test_template.id,
        })
        
        with self.assertRaises(ValidationError):
            self.env['lab.test.flow.line'].create({
                'flow_id': flow.id,
                'sequence': 10,
                'test_template_id': self.test_template.id,
            })

    def test_07_result_set_bulk_creation(self):
        """Test bulk creation performance of result lines"""
        criteria = []
        for i in range(50):
            criterion = self.env['lab.test.criterion'].create({
                'name': f'Test Criterion {i}',
                'code': f'TEST_{i:03d}',
                'test_type': 'numeric',
                'is_input_field': True,
                'sequence': i * 10,
            })
            criteria.append(criterion.id)
        
        large_template = self.env['lab.test.template'].create({
            'name': 'Large Test Template',
            'code': 'LTT001',
            'state': 'active',
            'criterion_ids': [(6, 0, criteria)]
        })
        
        result_set = self.env['lab.result.set'].create({
            'name': 'Large Result Set',
            'sample_id': self.env['lab.sample'].create({
                'product_id': self.sample_product.product_variant_id.id,
                'quantity': 1.0,
            }).id,
            'template_id': large_template.id,
                'number_of_samples': 20,
        })
        
        result_set._create_result_lines()
        
        expected_lines = 20 * 50
        self.assertEqual(len(result_set.result_line_ids), expected_lines)

    def test_08_complete_sample_success(self):
        """Test successful sample completion"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'task_id': self.task.id,
            'quantity': 5.0,
        })
        
        sample.action_start_testing()
        
        result_set = sample.result_set_ids[0]
        result_set.state = 'completed'
        
        sample.action_complete()
        
        self.assertEqual(sample.state, 'completed')

    def test_09_complete_sample_with_incomplete_results(self):
        """Test sample completion fails with incomplete results"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'task_id': self.task.id,
            'quantity': 5.0,
        })
        
        sample.action_start_testing()
        
        with self.assertRaises(UserError):
            sample.action_complete()

    def test_10_sample_reject(self):
        """Test sample rejection"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'task_id': self.task.id,
            'quantity': 5.0,
        })
        
        sample.action_reject()
        self.assertEqual(sample.state, 'rejected')

    def test_11_result_line_compliance_calculation(self):
        """Test result line compliance calculation"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'quantity': 1.0,
        })
        
        result_set = self.env['lab.result.set'].create({
            'name': 'Test Result Set',
            'sample_id': sample.id,
            'template_id': self.test_template.id,
            'number_of_samples': 1,
        })
        
        result_set._create_result_lines()
        
        strength_line = result_set.result_line_ids.filtered(
            lambda l: l.criterion_id.code == 'STRENGTH'
        )[0]
        strength_line.value_numeric = 30.0
        strength_line._compute_compliance()
        self.assertTrue(strength_line.is_compliant)
        
        strength_line.value_numeric = 60.0
        strength_line._compute_compliance()
        self.assertFalse(strength_line.is_compliant)

    def test_12_overall_result_calculation(self):
        """Test overall result calculation for result sets"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'quantity': 1.0,
        })
        
        result_set = self.env['lab.result.set'].create({
            'name': 'Test Result Set',
            'sample_id': sample.id,
            'template_id': self.test_template.id,
            'number_of_samples': 1,
        })
        
        result_set._create_result_lines()
        
        for line in result_set.result_line_ids:
            line.value_numeric = 25.0
            line._compute_compliance()
        
        result_set._compute_overall_result()
        self.assertEqual(result_set.overall_result, 'pass')
        
        result_set.result_line_ids[0].value_numeric = 100.0
        result_set.result_line_ids[0]._compute_compliance()
        
        result_set._compute_overall_result()
        self.assertEqual(result_set.overall_result, 'fail')

    def test_13_flow_next_step_progression(self):
        """Test flow progression through steps"""
        template2 = self.env['lab.test.template'].create({
            'name': 'Test Template 2',
            'code': 'TT002',
            'state': 'active',
            'criterion_ids': [(6, 0, [self.criterion_weight.id])]
        })
        
        multi_flow_template = self.env['lab.test.flow.template'].create({
            'name': 'Multi Step Flow',
            'line_ids': [
                (0, 0, {
                    'sequence': 10,
                    'test_template_id': self.test_template.id,
                    'sample_qty': 2,
                }),
                (0, 0, {
                    'sequence': 20,
                    'test_template_id': template2.id,
                    'sample_qty': 1,
                })
            ]
        })
        
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'quantity': 1.0,
        })
        
        flow = self.env['lab.test.flow'].create({
            'name': 'Multi Step Test',
            'sample_id': sample.id,
            'template_id': multi_flow_template.id,
        })
        
        action = flow.action_next_step()
        self.assertEqual(flow.current_step, 10)
        self.assertEqual(flow.state, 'in_progress')
        
        first_line = flow.line_ids.filtered(lambda l: l.sequence == 10)
        first_line.state = 'done'
        
        action = flow.action_next_step()
        self.assertEqual(flow.current_step, 20)
        
        second_line = flow.line_ids.filtered(lambda l: l.sequence == 20)
        second_line.state = 'done'
        
        flow.action_next_step()
        self.assertEqual(flow.state, 'completed')

    def test_14_error_handling_missing_template(self):
        """Test error handling for missing templates"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'quantity': 1.0,
        })
        
        self.sample_product.test_flow_template_id = False
        
        with self.assertRaises(UserError):
            sample.action_start_testing()

    def test_15_criteria_progress_calculation(self):
        """Test criteria progress percentage calculation"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'quantity': 1.0,
        })
        
        sample.action_start_testing()
        result_set = sample.result_set_ids[0]
        
        sample._compute_criteria_progress()
        self.assertEqual(sample.criteria_progress_percentage, 0.0)
        
        lines = result_set.result_line_ids
        for i, line in enumerate(lines[:len(lines)//2]):
            line.value_numeric = 25.0
        
        sample._compute_criteria_progress()
        self.assertAlmostEqual(sample.criteria_progress_percentage, 50.0, places=1)

    @patch('odoo.addons.appointment_products.models.lab_sample_clean.LabSample.message_post')
    def test_16_message_posting(self, mock_message_post):
        """Test that appropriate messages are posted during lifecycle"""
        sample = self.env['lab.sample'].create({
            'product_id': self.sample_product.product_variant_id.id,
            'quantity': 1.0,
        })
        
        sample.action_start_testing()
        
        mock_message_post.assert_called()
        
        result_set = sample.result_set_ids[0]
        result_set.state = 'completed'
        sample.action_complete()
        
        self.assertTrue(mock_message_post.call_count >= 2) 