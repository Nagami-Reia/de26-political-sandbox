import unittest

from kfrage_model.temporary_offices import TemporaryOfficeAssignment, TemporaryOfficeRegistry


class TemporaryOfficeTests(unittest.TestCase):
    def test_acting_office_expires_only_after_matching_successor_procedure(self):
        registry = TemporaryOfficeRegistry((TemporaryOfficeAssignment(
            assignment_id="cdu_mv_2026_interim",
            actor="Amthor",
            office="acting_cdu_mv_chair",
            begins_at="2026-09-22",
            ends_when="SUCCESSOR_FORMALLY_ELECTED",
        ),))
        offices = registry.apply_to_offices({"Amthor": ("chancellery_state_minister",)})
        self.assertEqual(
            offices["Amthor"],
            ("chancellery_state_minister", "acting_cdu_mv_chair"),
        )
        with self.assertRaises(ValueError):
            registry.resolve_successor(
                "cdu_mv_2026_interim", successor="Candidate A", elected_at="2027-02-01",
                procedure="FEDERAL_BOARD_APPOINTMENT",
            )
        registry.resolve_successor(
            "cdu_mv_2026_interim", successor="Candidate A", elected_at="2027-02-01",
            procedure="SUCCESSOR_FORMALLY_ELECTED",
        )
        offices = registry.apply_to_offices({"Amthor": ("chancellery_state_minister",)})
        self.assertEqual(offices["Amthor"], ("chancellery_state_minister",))


if __name__ == "__main__":
    unittest.main()
