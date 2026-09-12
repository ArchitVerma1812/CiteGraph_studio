import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QDialog, QGraphicsView

from citegraph.database import Database
from citegraph.main_window import MainWindow


class MainWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temp.name) / "gui.db")
        project_id = self.db.create_project("GUI test")
        self.window = MainWindow(self.db)
        self.window.open_project(project_id)

    def tearDown(self):
        self.window.close()
        self.temp.cleanup()

    def test_connect_action_can_be_toggled_off(self):
        paper_id = self.window._create_paper_now({"title": "Parent"}, QPointF(0, 0))
        self.window._select_node(paper_id)

        self.window.connect_action.trigger()
        self.assertEqual(self.window.connect_source_id, paper_id)
        self.assertTrue(self.window.connect_action.isChecked())

        self.window.connect_action.trigger()
        self.assertIsNone(self.window.connect_source_id)
        self.assertFalse(self.window.connect_action.isChecked())

    def test_canvas_uses_artifact_free_viewport_updates(self):
        self.assertEqual(
            self.window.view.viewportUpdateMode(),
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate,
        )

    def test_edge_bounds_include_the_painted_label(self):
        parent = self.window._create_paper_now({"title": "Parent"}, QPointF(0, 0))
        child = self.window._create_paper_now({"title": "Child"}, QPointF(0, 300))
        relation_id = self.window._create_relation_now(
            parent,
            child,
            {"relation_type": "method", "label": "A long dependency label"},
        )
        edge = self.window.edges[relation_id]

        self.assertTrue(edge.boundingRect().contains(edge._label_rect()))

    def test_project_chooser_can_be_cancelled(self):
        with patch("citegraph.main_window.ProjectChooserDialog") as chooser_class:
            chooser_class.return_value.exec.return_value = QDialog.DialogCode.Rejected

            self.window.choose_project()

        chooser_class.assert_called_once()

    def test_inspector_escapes_user_supplied_html(self):
        paper_id = self.window._create_paper_now(
            {"title": "<b>Title</b>", "authors": "<i>Author</i>"}, QPointF(0, 0)
        )
        self.window._select_node(paper_id)

        self.assertEqual(self.window.inspector_title.text(), "&lt;b&gt;Title&lt;/b&gt;")
        self.assertIn("&lt;i&gt;Author&lt;/i&gt;", self.window.inspector_body.text())


if __name__ == "__main__":
    unittest.main()
