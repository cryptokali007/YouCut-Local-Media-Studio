"""Opt-in QA mouse/keyboard transport using local files; no sockets or server."""
import json
from pathlib import Path
from PySide6.QtCore import Qt,QPoint,QPointF,QMimeData,QUrl,QEvent,QTimer
from PySide6.QtGui import QDragEnterEvent,QDropEvent,QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from .engine import ROOT

class Bridge:
    def __init__(self,window):
        self.window=window;self.last=None;self.directory=ROOT/'qa';self.directory.mkdir(exist_ok=True)
        self.timer=QTimer(window);self.timer.timeout.connect(self.tick);self.timer.start(100)

    def tick(self):
        try:r=json.loads((self.directory/'request.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):return
        if r['id']==self.last:return
        self.last=r['id']
        QTimer.singleShot(300,lambda:self.reply(r['id']))
        QTimer.singleShot(0,lambda:self.perform_safe(r))

    def perform_safe(self,r):
        try:self.perform(r)
        except Exception as error:self.reply(r['id'],str(error))

    def active(self):return QApplication.activePopupWidget() or QApplication.activeModalWidget() or self.window

    def perform(self,r):
        window=self.active();kind=r['action']
        if kind=='screenshot':return
        position=QPoint(int(r.get('x',0)),int(r.get('y',0)))
        widget=window.childAt(position) or window
        point=widget.mapFrom(window,position)
        if kind in {'click','doubleclick'}:
            (QTest.mouseDClick if kind=='doubleclick' else QTest.mouseClick)(widget,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        elif kind=='type':
            focus=QApplication.focusWidget() or window.focusWidget()
            if focus is None:raise ValueError('Click a text field before typing.')
            if focus:
                for char in r['text']:
                    if char=='\n':
                        QTest.keyClick(focus,Qt.Key.Key_Return)
                        continue
                    QApplication.sendEvent(focus,QKeyEvent(QEvent.Type.KeyPress,0,Qt.KeyboardModifier.NoModifier,char))
                    QApplication.sendEvent(focus,QKeyEvent(QEvent.Type.KeyRelease,0,Qt.KeyboardModifier.NoModifier,char))
        elif kind=='key':
            key=r['key'].lower();mod=Qt.KeyboardModifier.ControlModifier if key.startswith('ctrl+') else Qt.KeyboardModifier.NoModifier
            key=key.removeprefix('ctrl+')
            keys={'tab':Qt.Key.Key_Tab,'enter':Qt.Key.Key_Return,'escape':Qt.Key.Key_Escape,'space':Qt.Key.Key_Space,'down':Qt.Key.Key_Down,'up':Qt.Key.Key_Up,'delete':Qt.Key.Key_Delete,'home':Qt.Key.Key_Home,'end':Qt.Key.Key_End}
            QTest.keyClick(QApplication.focusWidget() or window.focusWidget() or window,keys.get(key,ord(key.upper()) if len(key)==1 else Qt.Key.Key_unknown),mod)
        elif kind=='drop':
            mime=QMimeData();mime.setUrls([QUrl.fromLocalFile(str(Path(p).resolve())) for p in r['paths']])
            enter=QDragEnterEvent(point,Qt.DropAction.CopyAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(widget,enter)
            drop=QDropEvent(QPointF(point),Qt.DropAction.CopyAction,mime,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(widget,drop)
        else:raise ValueError('Allowed actions: screenshot, click, doubleclick, type, key, drop')

    def reply(self,identifier,error=None):
        path=self.directory/'screen.png';window=self.active();window.grab().toImage().scaled(window.width(),window.height()).save(str(path))
        data=dict(id=identifier,screenshot=str(path),width=window.width(),height=window.height(),title=window.windowTitle())
        if error:data['error']=error
        (self.directory/('response-'+identifier+'.json')).write_text(json.dumps(data),encoding='utf-8')
