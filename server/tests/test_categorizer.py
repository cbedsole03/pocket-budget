import unittest

from app.categorizer import category_for_transaction, normalize


class CategorizerTests(unittest.TestCase):
    def test_normalize_compacts_case_and_space(self):
        self.assertEqual(normalize("  DoorDash   Inc "), "doordash inc")

    def test_income_goes_to_income(self):
        tx = {"amount": -2500.00, "personal_finance_category": {"primary": "INCOME"}}
        self.assertEqual(category_for_transaction(tx), "income")

    def test_rent_maps_to_necessities(self):
        tx = {"amount": 1200.00, "personal_finance_category": {"primary": "RENT_AND_UTILITIES"}}
        self.assertEqual(category_for_transaction(tx), "necessities")

    def test_merchant_rule_wins(self):
        tx = {
            "amount": 80.00,
            "merchant_name": "Flower Shop",
            "personal_finance_category": {"primary": "GENERAL_MERCHANDISE"},
        }
        rules = [{"match_type": "merchant_contains", "pattern": "flower", "category_id": "girlfriend"}]
        self.assertEqual(category_for_transaction(tx, rules), "girlfriend")


if __name__ == "__main__":
    unittest.main()

