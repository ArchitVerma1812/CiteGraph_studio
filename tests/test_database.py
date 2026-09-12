import tempfile
import unittest
from pathlib import Path

from citegraph.database import Database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "test.db")
        self.project_id = self.db.create_project("Test project")

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_project_graph_round_trip(self):
        a = self.db.insert_paper(self.project_id, {"title": "Parent"}, 10, 20)
        b = self.db.insert_paper(self.project_id, {"title": "Child"}, 30, 40)
        relation = self.db.insert_relation(
            self.project_id, a, b, {"relation_type": "method", "label": "RK4"}
        )
        self.assertEqual(len(self.db.list_papers(self.project_id)), 2)
        self.assertEqual(self.db.get_relation(relation)["parent_id"], a)
        self.assertFalse(self.db.would_create_cycle(self.project_id, a, b))
        self.assertTrue(self.db.would_create_cycle(self.project_id, b, a))

        payload = self.db.export_project(self.project_id)
        imported_id = self.db.import_project(payload, "Imported")
        self.assertEqual(len(self.db.list_papers(imported_id)), 2)
        self.assertEqual(len(self.db.list_relations(imported_id)), 1)

    def test_cascade_delete(self):
        a = self.db.insert_paper(self.project_id, {"title": "A"}, 0, 0)
        b = self.db.insert_paper(self.project_id, {"title": "B"}, 0, 0)
        self.db.insert_relation(self.project_id, a, b, {})
        self.db.delete_paper(a)
        self.assertEqual(self.db.list_relations(self.project_id), [])

    def test_failed_import_is_atomic(self):
        payload = {
            "format": "citegraph-studio",
            "version": 1,
            "project": {"name": "Broken import"},
            "papers": [{"id": 1, "title": "Bad position", "x": "not-a-number"}],
            "relations": [],
        }
        project_count = len(self.db.list_projects())

        with self.assertRaisesRegex(ValueError, "invalid position"):
            self.db.import_project(payload)

        self.assertEqual(len(self.db.list_projects()), project_count)

    def test_relation_endpoints_must_belong_to_project(self):
        other_project = self.db.create_project("Other")
        parent = self.db.insert_paper(self.project_id, {"title": "Parent"}, 0, 0)
        child = self.db.insert_paper(other_project, {"title": "Child"}, 0, 0)

        with self.assertRaisesRegex(ValueError, "endpoints"):
            self.db.insert_relation(self.project_id, parent, child, {})

        self.assertEqual(self.db.list_relations(self.project_id), [])

    def test_relation_type_update_rejects_duplicates_without_mutating(self):
        parent = self.db.insert_paper(self.project_id, {"title": "Parent"}, 0, 0)
        child = self.db.insert_paper(self.project_id, {"title": "Child"}, 0, 0)
        self.db.insert_relation(
            self.project_id, parent, child, {"relation_type": "cites"}
        )
        method_id = self.db.insert_relation(
            self.project_id, parent, child, {"relation_type": "method"}
        )

        with self.assertRaisesRegex(ValueError, "already exists"):
            self.db.update_relation(method_id, {"relation_type": "cites"})

        self.assertEqual(self.db.get_relation(method_id)["relation_type"], "method")

    def test_relation_insert_rejects_cycle(self):
        a = self.db.insert_paper(self.project_id, {"title": "A"}, 0, 0)
        b = self.db.insert_paper(self.project_id, {"title": "B"}, 0, 0)
        self.db.insert_relation(self.project_id, a, b, {})

        with self.assertRaisesRegex(ValueError, "cycle"):
            self.db.insert_relation(self.project_id, b, a, {})

        self.assertEqual(len(self.db.list_relations(self.project_id)), 1)

    def test_import_rejects_cycles_atomically(self):
        payload = {
            "format": "citegraph-studio",
            "version": 1,
            "project": {"name": "Cyclic"},
            "papers": [{"id": 1, "title": "A"}, {"id": 2, "title": "B"}],
            "relations": [
                {"parent_id": 1, "child_id": 2},
                {"parent_id": 2, "child_id": 1},
            ],
        }
        project_count = len(self.db.list_projects())

        with self.assertRaisesRegex(ValueError, "cycle"):
            self.db.import_project(payload)

        self.assertEqual(len(self.db.list_projects()), project_count)

    def test_import_rejects_duplicate_paper_ids_atomically(self):
        payload = {
            "format": "citegraph-studio",
            "version": 1,
            "project": {"name": "Duplicates"},
            "papers": [{"id": 7, "title": "A"}, {"id": 7, "title": "B"}],
            "relations": [],
        }
        project_count = len(self.db.list_projects())

        with self.assertRaisesRegex(ValueError, "Duplicate imported paper id"):
            self.db.import_project(payload)

        self.assertEqual(len(self.db.list_projects()), project_count)

    def test_import_rejects_unknown_relation_endpoints_atomically(self):
        payload = {
            "format": "citegraph-studio",
            "version": 1,
            "project": {"name": "Dangling relation"},
            "papers": [{"id": 1, "title": "A"}],
            "relations": [{"parent_id": 1, "child_id": 99}],
        }
        project_count = len(self.db.list_projects())

        with self.assertRaisesRegex(ValueError, "unknown paper"):
            self.db.import_project(payload)

        self.assertEqual(len(self.db.list_projects()), project_count)


if __name__ == "__main__":
    unittest.main()
