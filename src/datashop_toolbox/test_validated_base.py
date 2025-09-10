import unittest
from datetime import datetime
from typing import Optional
from pydantic import ValidationError
from datashop_toolbox.basehdr import BaseHeader
from datashop_toolbox.validated_base import ValidatedBase

class SampleModel(ValidatedBase):
    cruise_date: Optional[str] = None
    temperature: Optional[float] = None
    station_id: Optional[int] = None
    notes: Optional[str] = None
    values: Optional[list[str]] = None

class TestValidatedBase(unittest.TestCase):

    def test_none_values(self):
        model = SampleModel()
        self.assertEqual(model.temperature, BaseHeader.NULL_VALUE)
        self.assertEqual(model.station_id, int(BaseHeader.NULL_VALUE))
        self.assertEqual(model.cruise_date, BaseHeader.SYTM_NULL_VALUE)
        self.assertEqual(model.values, [])

    def test_fortran_exponent(self):
        model = SampleModel(notes="1.23D4")
        self.assertEqual(model.notes, "1.23E4")

    def test_strip_quotes_and_spaces(self):
        model = SampleModel(notes="  'quoted text'  ")
        self.assertEqual(model.notes, "quoted text")

    def test_valid_date_format(self):
        valid_date = "2023-09-10 10:45:43.000"
        model = SampleModel(cruise_date=valid_date)
        expected = datetime.strptime(valid_date, BaseHeader.SYTM_FORMAT).strftime(BaseHeader.SYTM_FORMAT)[:-4].upper()
        self.assertEqual(model.cruise_date, expected)

    def test_invalid_date_format(self):
        with self.assertRaises(ValidationError) as context:
            SampleModel(cruise_date="10-09-2023")
        self.assertIn("Invalid date format", str(context.exception))

if __name__ == "__main__":
    unittest.main()
