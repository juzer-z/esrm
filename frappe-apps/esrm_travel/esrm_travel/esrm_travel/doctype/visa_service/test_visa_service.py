from frappe.tests.utils import FrappeTestCase

from esrm_travel.esrm_travel.doctype.visa_service.visa_service import (
    mask_passport,
    parse_required_documents,
)


class TestVisaService(FrappeTestCase):
    def test_masks_passport_for_invoice(self):
        self.assertEqual(mask_passport("A1234567"), "A*****67")
        self.assertEqual(mask_passport("1234"), "1234")

    def test_parses_unique_required_documents(self):
        self.assertEqual(
            parse_required_documents("Passport Copy\nPhoto, Bank Statement\nPhoto"),
            ["Passport Copy", "Photo", "Bank Statement"],
        )
