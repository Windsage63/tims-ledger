from __future__ import annotations

import unittest

from .db_harness import DatabaseHarness, FixtureLoader


class ApiTestCase(unittest.TestCase):
    fixture_loader: FixtureLoader | None = None

    def setUp(self) -> None:
        self.harness = DatabaseHarness(type(self).fixture_loader)
        self.client = self.harness.start()
        self.settings = self.harness.settings
        self.temp_dir = self.harness.temp_dir

    def tearDown(self) -> None:
        self.harness.close()
        self.client = None
        self.settings = None
        self.temp_dir = None
