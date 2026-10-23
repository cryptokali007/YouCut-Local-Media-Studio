"""Entry point. No server, browser launch, account, or network initialization."""
from pathlib import Path
import os
import sys
import traceback

ROOT=Path(__file__).resolve().parent
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
os.environ['DO_NOT_TRACK']='1'
os.environ['TOKENIZERS_PARALLELISM']='false'
os.environ['OMP_NUM_THREADS']='4'
os.environ['QT_FFMPEG_DECODING_HW_DEVICE_TYPES']=''
for folder in ['outputs','work','logs','models']:(ROOT/folder).mkdir(exist_ok=True)
if sys.stdout is None:sys.stdout=(ROOT/'logs/app.log').open('a',encoding='utf-8')
if sys.stderr is None:sys.stderr=sys.stdout

def main():
    from PySide6.QtWidgets import QApplication,QMessageBox
    from media_workbench.ui import Window,STYLE
    from media_workbench.engine import binaries
    if '--qa' in sys.argv:
        from PySide6.QtCore import Qt
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontUseNativeDialogs,True)
    app=QApplication(sys.argv)
    from PySide6.QtGui import QPalette,QColor
    palette=QPalette()
    for role,color in [(QPalette.ColorRole.Window,'#f2f4f6'),(QPalette.ColorRole.WindowText,'#17252e'),
                       (QPalette.ColorRole.Base,'#ffffff'),(QPalette.ColorRole.AlternateBase,'#edf2f4'),
                       (QPalette.ColorRole.Text,'#17252e'),(QPalette.ColorRole.Button,'#ffffff'),
                       (QPalette.ColorRole.ButtonText,'#192f38'),(QPalette.ColorRole.Highlight,'#156963'),
                       (QPalette.ColorRole.HighlightedText,'#ffffff'),(QPalette.ColorRole.ToolTipBase,'#ffffff'),
                       (QPalette.ColorRole.ToolTipText,'#17252e'),(QPalette.ColorRole.Link,'#156963')]:
        palette.setColor(role,QColor(color))
    app.setApplicationName('YouCutOwn Studio');app.setOrganizationName('LocalTools');app.setStyle('Fusion');app.setPalette(palette);app.setStyleSheet(STYLE)
    try:binaries()
    except Exception as error:QMessageBox.critical(None,'YouCutOwn Studio',str(error));return 1
    window=Window();window.show()
    if '--qa' in sys.argv:
        print('QA: initializing controller',flush=True)
        from media_workbench.qa_bridge import Bridge
        window.qa_bridge=Bridge(window)
        print('QA: controller initialized',flush=True)
    if '--smoke' in sys.argv:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500,lambda:(window.grab().save(str(ROOT/'work/ui-smoke.png')),window.close()))
    return app.exec()

if __name__=='__main__':
    try:sys.exit(main())
    except Exception:
        traceback.print_exc()
        raise
