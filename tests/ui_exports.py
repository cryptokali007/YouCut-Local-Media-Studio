"""Click the native converter button and verify actual files for every format."""
from pathlib import Path
import json
import os
import sys
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton
from media_workbench.ui import Window, STYLE
from media_workbench.engine import probe


def main():
    app = QApplication([])
    app.setStyleSheet(STYLE)
    window = Window()
    folder = ROOT / 'app/tests/results/image-formats'
    window.state_path = folder / 'ui-settings.json'
    window.output_dir.setText(str(folder))
    window.output_size.setCurrentText('Original')
    window.imported([probe(str(folder / 'Source odd size é.png'))])
    window.tabs.setCurrentIndex(5)
    window.show()
    app.processEvents()
    button = next(b for b in window.tabs.widget(5).findChildren(QPushButton)
                  if b.text() == 'Resize / convert selected image')
    failures = []
    window.failed = failures.append
    for label, suffix in [('High-quality JPEG / JPG', '.jpg'), ('Lossless WebP', '.webp'), ('PNG', '.png')]:
        window.image_format.setCurrentText(label)
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        deadline = time.monotonic() + 45
        while window.worker is not None and time.monotonic() < deadline:
            app.processEvents()
            QTest.qWait(20)
        if window.worker is not None:
            window.cancel_job()
            window.worker.wait(10000)
            raise AssertionError('Image export did not complete in time')
        assert not failures, failures
        assert Path(window.last_output).suffix == suffix and Path(window.last_output).is_file()
        assert json.loads(window.state_path.read_text())['image_format'] == label
        print('PASS native converter button:', label, flush=True)
    window.close()
    app.processEvents()


if __name__ == '__main__':
    main()
