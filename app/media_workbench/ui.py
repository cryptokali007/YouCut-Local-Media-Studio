"""Native Qt interface: three buckets and one operation at a time."""
from pathlib import Path
import json
import os

from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer, QSize
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QPixmap, QShortcut, QKeySequence
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, QFileDialog,
    QMessageBox, QTabWidget, QFormLayout, QComboBox, QCheckBox, QDoubleSpinBox, QSpinBox,
    QLineEdit, QPlainTextEdit, QProgressBar, QSlider, QGroupBox, QSplitter, QScrollArea, QDialog, QTextBrowser)

from .engine import ROOT, Job, Cancelled, probe
from .captions import seconds, to_srt, parse_srt


class Worker(QThread):
    progress = Signal(str, int)
    result = Signal(object)
    failure = Signal(str)

    def __init__(self, action):
        super().__init__()
        self.action = action

    def run(self):
        try:
            self.result.emit(self.action())
        except Exception as error:
            self.failure.emit(str(error))


class Bucket(QGroupBox):
    selected = Signal(str)
    dropped = Signal(list)

    def __init__(self, title, kind):
        super().__init__(title)
        self.kind = kind
        self.directory=str(Path.home()/{'video':'Videos','audio':'Music','image':'Pictures'}[kind])
        if not Path(self.directory).exists():self.directory=str(Path.home())
        layout = QVBoxLayout(self)
        self.list = DropList()
        self.list.paths.connect(self.dropped)
        self.list.itemSelectionChanged.connect(self.selection_changed)
        layout.addWidget(self.list)
        actions = QHBoxLayout()
        for title, action in [('Add…',self.add_dialog),('↑',lambda:self.move(-1)),('↓',lambda:self.move(1)),('Remove',self.remove)]:
            button=QPushButton(title); button.clicked.connect(action); actions.addWidget(button)
        layout.addLayout(actions)
        self.list.setToolTip('Drop files here. Drag rows or use the arrows to change order. Selected row is used for single-file tools.')

    def add_dialog(self):
        files,_=QFileDialog.getOpenFileNames(self,'Add '+self.kind+' files',self.directory,'Media files (*.*)')
        if files:
            self.directory=str(Path(files[0]).parent)
            self.dropped.emit(files)

    def add(self, media):
        path=media['path']
        if path in self.paths():return
        detail=f'{media["duration"]:.1f}s' if media['kind']!='image' else f'{media["width"]}×{media["height"]}'
        item=QListWidgetItem(Path(path).name+'  ·  '+detail)
        item.setData(Qt.ItemDataRole.UserRole,path)
        item.setToolTip(path)
        self.list.addItem(item)
        if self.list.count()==1:self.list.setCurrentItem(item)

    def selection_changed(self):
        item=self.list.currentItem()
        if item:self.selected.emit(item.data(Qt.ItemDataRole.UserRole))

    def paths(self):
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())]

    def chosen(self):
        item=self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else (self.paths()[0] if self.paths() else None)

    def remove(self):
        for item in self.list.selectedItems():self.list.takeItem(self.list.row(item))

    def move(self,delta):
        row=self.list.currentRow(); target=row+delta
        if 0<=target<self.list.count():
            item=self.list.takeItem(row);self.list.insertItem(target,item);self.list.setCurrentItem(item)


class DropList(QListWidget):
    paths=Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setMinimumHeight(95)

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():event.acceptProposedAction()
        else:super().dragEnterEvent(event)

    def dragMoveEvent(self,event):
        if event.mimeData().hasUrls():event.acceptProposedAction()
        else:super().dragMoveEvent(event)

    def dropEvent(self,event):
        if event.mimeData().hasUrls():
            self.paths.emit([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])
            event.acceptProposedAction()
        else:super().dropEvent(event)


def combo(values):
    widget=QComboBox();widget.addItems(values);return widget


def number(low,high,value,step=.1):
    widget=QDoubleSpinBox();widget.setRange(low,high);widget.setValue(value);widget.setSingleStep(step);widget.setDecimals(2);return widget


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('YouCutOwn Studio — offline · Python + FFmpeg')
        self.resize(1230,920)
        self.setMinimumSize(980,760)
        self.worker=None;self.job=None;self.media={};self.last_output=None
        self.transcript_source=None;self.word_segments=None;self.closing=False
        self.state_path=ROOT/'settings.json'
        try:self.settings=json.loads(self.state_path.read_text(encoding='utf-8'))
        except (OSError,ValueError):self.settings={}
        container=QWidget();self.setCentralWidget(container);layout=QVBoxLayout(container)
        title=QHBoxLayout();name=QLabel('YouCutOwn Studio');name.setObjectName('title');title.addWidget(name)
        title.addStretch();title.addWidget(QLabel('LOCAL FILES  •  NO ACCOUNT  •  OFFLINE'))
        guide=QPushButton('How to use');guide.clicked.connect(self.show_guide);title.addWidget(guide);layout.addLayout(title)
        self.hint=QLabel('1  Drop files below     2  Choose a tool     3  Export a new file')
        layout.addWidget(self.hint)
        bins=QHBoxLayout();self.buckets={}
        for kind,title_text in [('video','Videos'),('audio','Audio / music'),('image','Images / watermark')]:
            bucket=Bucket(title_text,kind);bucket.directory=self.settings.get('last_dir_'+kind,bucket.directory)
            bucket.dropped.connect(self.import_files);bucket.selected.connect(self.preview)
            bins.addWidget(bucket);self.buckets[kind]=bucket
        layout.addLayout(bins,2)
        split=QSplitter(Qt.Orientation.Horizontal);layout.addWidget(split,6)
        preview=QWidget();pv=QVBoxLayout(preview);pv.setContentsMargins(0,0,8,0)
        self.video=QVideoWidget();self.video.setMinimumSize(360,200);pv.addWidget(self.video,1)
        self.image_preview=QLabel();self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.image_preview.hide();pv.addWidget(self.image_preview,1)
        self.preview_name=QLabel('Select a file to preview');self.preview_name.setWordWrap(True);pv.addWidget(self.preview_name)
        self.player=QMediaPlayer(self);self.audio_output=QAudioOutput(self);self.audio_output.setVolume(.45)
        self.player.setAudioOutput(self.audio_output);self.player.setVideoOutput(self.video)
        controls=QHBoxLayout();self.play=QPushButton('Play / pause');self.play.clicked.connect(self.toggle_play);controls.addWidget(self.play)
        self.seek=QSlider(Qt.Orientation.Horizontal);self.seek.sliderMoved.connect(self.player.setPosition);controls.addWidget(self.seek)
        self.time_label=QLabel('00:00 / 00:00');controls.addWidget(self.time_label);pv.addLayout(controls)
        self.player.durationChanged.connect(lambda d:self.seek.setRange(0,d))
        self.player.positionChanged.connect(self.position_changed)
        self.player.errorOccurred.connect(lambda *_:self.statusBar().showMessage('Preview unavailable for this codec; export may still work.'))
        extra=QHBoxLayout()
        self.set_in=QPushButton('Use playhead as start');self.set_in.clicked.connect(lambda:self.start.setText(f'{self.player.position()/1000:.3f}'));extra.addWidget(self.set_in)
        self.set_out=QPushButton('Use playhead as end');self.set_out.clicked.connect(lambda:self.end.setText(f'{self.player.position()/1000:.3f}'));extra.addWidget(self.set_out);pv.addLayout(extra)
        split.addWidget(preview)
        self.tabs=QTabWidget();split.addWidget(self.tabs);split.setSizes([570,600])
        self.add_edit_tab();self.add_join_tab();self.add_music_tab();self.add_caption_tab();self.add_voice_tab();self.add_tools_tab()
        options=QHBoxLayout()
        self.output_size=combo(['Original','1080p','720p','Vertical','Square']);self.output_size.setCurrentText(self.settings.get('size','Original'))
        self.fit=combo(['Fit','Fill / crop']);self.encoder=combo(['CPU quality','NVIDIA'])
        options.addWidget(QLabel('Output size'));options.addWidget(self.output_size);options.addWidget(self.fit)
        options.addWidget(QLabel('Encoder'));options.addWidget(self.encoder)
        self.watermark=QCheckBox('Add selected image as watermark');options.addWidget(self.watermark)
        self.corner=combo(['Bottom right','Bottom left','Top right','Top left']);options.addWidget(self.corner)
        layout.addLayout(options)
        self.watermark.setToolTip('Uses the selected row in Images. Applies to video exports, including joins, music and captions.')
        destination=QHBoxLayout();destination.addWidget(QLabel('Save new files to'))
        self.output_dir=QLineEdit(self.settings.get('output_dir',str(ROOT/'outputs')));destination.addWidget(self.output_dir)
        browse=QPushButton('Browse…');browse.clicked.connect(self.choose_output);destination.addWidget(browse)
        open_dir=QPushButton('Open folder');open_dir.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_dir.text())));destination.addWidget(open_dir)
        layout.addLayout(destination)
        bottom=QHBoxLayout();self.status=QLabel('Ready');self.status.setWordWrap(True);bottom.addWidget(self.status,2)
        self.progress=QProgressBar();self.progress.setValue(0);bottom.addWidget(self.progress,1)
        self.cancel=QPushButton('Cancel');self.cancel.setEnabled(False);self.cancel.clicked.connect(self.cancel_job);bottom.addWidget(self.cancel)
        self.open_result=QPushButton('Preview last result');self.open_result.setEnabled(False);self.open_result.clicked.connect(self.preview_result);bottom.addWidget(self.open_result)
        self.add_result=QPushButton('Add result to bucket');self.add_result.setEnabled(False);self.add_result.clicked.connect(lambda:self.import_files([self.last_output]) if self.last_output else None);bottom.addWidget(self.add_result)
        layout.addLayout(bottom)
        self.statusBar().showMessage('One operation at a time. Originals are preserved. Nothing is uploaded.')
        menu=self.menuBar().addMenu('Project')
        for text,action in [('Save project…',self.save_project),('Open project…',self.load_project),('Clear buckets',self.clear_buckets),('Open guide',self.show_guide)]:
            act=QAction(text,self);act.triggered.connect(action);menu.addAction(act)
        for label in self.tabs.findChildren(QLabel):label.setWordWrap(True)

    def tab(self,name):
        page=QWidget();form=QFormLayout(page);form.setContentsMargins(14,14,14,14);form.setSpacing(10)
        self.tabs.addTab(page,name);return form

    def action_button(self,form,label,operation):
        button=QPushButton(label);button.setObjectName('primary');button.setMinimumHeight(36)
        button.clicked.connect(lambda:self.start_operation(operation));form.addRow(button);return button

    def add_edit_tab(self):
        form=self.tab('Trim / speed')
        form.addRow(QLabel('Uses the selected video. Export applies trim, speed and output size together.'))
        self.start=QLineEdit('0');self.end=QLineEdit();self.end.setPlaceholderText('Blank = end of video')
        form.addRow('Start (seconds or HH:MM:SS)',self.start);form.addRow('End',self.end)
        self.speed=combo(['0.25','0.5','1','2','4','8','16','32','64','128','256']);self.speed.setEditable(True);self.speed.setCurrentText('1')
        self.speed.currentTextChanged.connect(self.speed_changed);form.addRow('Speed × (or type a custom value)',self.speed)
        self.keep_audio=QCheckBox('Keep original audio (preserve pitch)');self.keep_audio.setChecked(True);form.addRow(self.keep_audio)
        self.duration_hint=QLabel('At 256×, 1 hour becomes about 14 seconds.');self.duration_hint.setWordWrap(True);form.addRow(self.duration_hint)
        self.action_button(form,'Export trimmed / sped-up video','edit')
        form.addRow(QLabel('Tip: click “Use playhead as start/end” under the player to set a trim.'))

    def add_join_tab(self):
        form=self.tab('Join / slides')
        form.addRow(QLabel('Uses every video in bucket order. Drag rows or use ↑ / ↓ to reorder.'))
        self.transition=combo(['None','Crossfade','Fade through black','Wipe left','Slide left','Dissolve'])
        form.addRow('Between clips',self.transition)
        self.transition_duration=number(.1,5,.5);form.addRow('Transition seconds',self.transition_duration)
        self.action_button(form,'Join all videos','join')
        self.slide_duration=number(.5,120,4,.5);form.addRow('Seconds per image',self.slide_duration)
        self.action_button(form,'Make slideshow from all images','slideshow')
        form.addRow(QLabel('Transitions overlap clips, making the result shorter than a hard-cut join.\nTo add music afterward, add the result and use Music.'))

    def add_music_tab(self):
        form=self.tab('Music')
        form.addRow(QLabel('Uses the selected video and selected audio track.'))
        self.loop=QCheckBox('Loop video to match full music length');self.loop.setChecked(True);form.addRow(self.loop)
        self.mix=QCheckBox('Mix with original sound (otherwise replace it)');form.addRow(self.mix)
        self.music_volume=number(0,2,1);self.original_volume=number(0,2,.4)
        form.addRow('Music volume (1 = full)',self.music_volume);form.addRow('Original volume',self.original_volume)
        self.action_button(form,'Export video with music','music')
        form.addRow(QLabel('With looping off, video duration is preserved; shorter music is padded with silence.'))

    def add_caption_tab(self):
        form=self.tab('Subtitles')
        self.caption_source_label=QLabel('1. Select a video, then transcribe or import an SRT.');self.caption_source_label.setWordWrap(True);form.addRow(self.caption_source_label)
        self.model=combo(['base.en — English / faster','small — multilingual / more accurate']);form.addRow('Offline speech model',self.model)
        self.action_button(form,'1  Transcribe selected video / audio','transcribe')
        line=QHBoxLayout()
        for text,fn in [('Import SRT…',self.import_srt),('Save SRT…',self.save_srt)]:
            b=QPushButton(text);b.clicked.connect(fn);line.addWidget(b)
        form.addRow(line)
        self.srt=QPlainTextEdit();self.srt.setPlaceholderText('Editable subtitles appear here. Correct the words or timestamps before exporting.');self.srt.setMinimumHeight(110);form.addRow(self.srt)
        styling=QHBoxLayout();self.caption_style=combo(['Highlight','Outlined','Boxed']);styling.addWidget(self.caption_style)
        self.caption_position=combo(['Bottom','Center','Top']);styling.addWidget(self.caption_position)
        self.font_size=QSpinBox();self.font_size.setRange(20,120);self.font_size.setValue(48);self.font_size.setSuffix(' px at 1080p');styling.addWidget(self.font_size);form.addRow(styling)
        self.action_button(form,'2  Export video with these subtitles','captions')

    def add_voice_tab(self):
        form=self.tab('Kokoro voice')
        form.addRow(QLabel('Local Kokoro text-to-speech. Creates a WAV for the Audio bucket.'))
        self.voice_text=QPlainTextEdit();self.voice_text.setPlaceholderText('Type narration here…');form.addRow(self.voice_text)
        self.voice=combo(['af_heart','af_bella','af_nicole','am_adam','am_michael','bf_emma','bm_george'])
        form.addRow('Voice',self.voice);self.voice_speed=number(.5,2,1);form.addRow('Speaking speed',self.voice_speed)
        self.action_button(form,'Generate voice WAV','voice')
        form.addRow(QLabel('Then click “Add result to bucket” and use Music to add it to a video.'))

    def add_tools_tab(self):
        form=self.tab('Extra tools')
        form.addRow(QLabel('Small useful tools. Single-file tools use the selected row.'))
        for label,op in [('Extract video audio to WAV','extract_audio'),('Join all audio tracks to WAV','join_audio'),
                         ('Normalize selected audio loudness','normalize_audio')]:
            self.action_button(form,label,op)
        self.image_format=combo(['PNG','High-quality JPEG / JPG','Lossless WebP'])
        self.image_format.setCurrentText(self.settings.get('image_format','PNG'))
        self.image_format.setToolTip('JPEG: quality 95, full color detail, white behind transparency. WebP: lossless, including transparency.')
        form.addRow('Image file type',self.image_format)
        self.action_button(form,'Resize / convert selected image','image')
        self.action_button(form,'Save video frame at trim start','frame')
        form.addRow(QLabel('Output size and Fit / Fill controls below also apply to images and frames.'))

    def speed_changed(self,text):
        try:
            speed=float(text.rstrip('x×'))
            if hasattr(self,'keep_audio'):self.keep_audio.setChecked(speed<8)
        except ValueError:pass

    def import_files(self,paths):
        if self.worker:
            QMessageBox.information(self,'Please wait','Finish or cancel the current operation before adding files.');return
        candidates=[]
        for path in paths:
            p=Path(path)
            if p.is_file():candidates.append(str(p.resolve()))
        if not candidates:return
        self.begin_worker(lambda:[probe(p) for p in candidates],self.imported,'Reading media information…')

    def imported(self,items):
        for info in items:
            self.media[info['path']]=info;self.buckets[info['kind']].directory=str(Path(info['path']).parent)
            self.buckets[info['kind']].add(info)
        self.status.setText(f'Added {len(items)} file(s). Select a tool to continue.')

    def preview(self,path):
        self.player.stop()
        self.preview_path=path
        self.preview_name.setText(Path(path).name)
        info=self.media.get(path,{})
        if info.get('kind')=='image':
            self.video.hide();self.image_preview.show();pix=QPixmap(path)
            self.image_preview.setPixmap(pix.scaled(QSize(540,310),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
            self.player.setSource(QUrl())
        else:
            self.image_preview.hide();self.video.show();self.player.setSource(QUrl.fromLocalFile(path))

    def toggle_play(self):
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.player.pause()
        else:self.player.play()

    def position_changed(self,position):
        if not self.seek.isSliderDown():self.seek.setValue(position)
        def stamp(ms):return f'{int(ms//60000):02}:{int(ms//1000)%60:02}'
        self.time_label.setText(stamp(position)+' / '+stamp(self.player.duration()))

    def build_spec(self,operation):
        def selected(kind):
            p=self.buckets[kind].chosen();return [p] if p else []
        spec=dict(operation=operation, videos=self.buckets['video'].paths() if operation=='join' else selected('video'),
                  audio=self.buckets['audio'].paths() if operation=='join_audio' else selected('audio'),images=self.buckets['image'].paths() if operation=='slideshow' else selected('image'),
                  output_dir=self.output_dir.text(),size=self.output_size.currentText(),fit=self.fit.currentText(),
                  encoder='NVIDIA' if self.encoder.currentText()=='NVIDIA' else 'CPU',
                  transition={'None':'none','Crossfade':'fade','Fade through black':'fadeblack','Wipe left':'wipeleft','Slide left':'slideleft','Dissolve':'dissolve'}[self.transition.currentText()],
                  transition_duration=self.transition_duration.value(),slide_duration=self.slide_duration.value(),
                  corner=self.corner.currentText())
        if self.watermark.isChecked():
            wm=self.buckets['image'].chosen()
            if not wm:raise ValueError('Add and select an image for the watermark, or untick the watermark option.')
            spec['watermark']=wm
        if operation in {'edit','frame'}:
            spec.update(start=seconds(self.start.text() or '0'),end=seconds(self.end.text()) if self.end.text().strip() else 0,
                        speed=float(self.speed.currentText().rstrip('x×')),keep_audio=self.keep_audio.isChecked())
        elif operation=='music':
            spec.update(loop=self.loop.isChecked(),mix=self.mix.isChecked(),music_volume=self.music_volume.value(),original_volume=self.original_volume.value())
        elif operation=='transcribe':
            if getattr(self,'preview_path',None) in self.buckets['audio'].paths():spec['videos']=[]
            spec['model']='small' if self.model.currentIndex() else 'base.en'
        elif operation=='captions':
            source=self.buckets['video'].chosen()
            if not self.transcript_source or source!=self.transcript_source:
                raise ValueError('These subtitles belong to a different source. Select the original video again, or transcribe/import subtitles for the selected video.')
            parse_srt(self.srt.toPlainText())
            spec.update(subtitles=self.srt.toPlainText(),caption_style=self.caption_style.currentText(),
                        caption_position=self.caption_position.currentText(),font_size=self.font_size.value(),word_segments=self.word_segments)
        elif operation=='voice':
            spec.update(text=self.voice_text.toPlainText(),voice=self.voice.currentText(),voice_speed=self.voice_speed.value())
        elif operation=='image':
            spec['image_format']=['PNG','JPEG','WebP'][self.image_format.currentIndex()]
        return spec

    def start_operation(self,operation):
        if self.worker:return
        try:
            spec=self.build_spec(operation)
            self.job=Job(spec,lambda message,percent:self.worker.progress.emit(message,percent))
        except Exception as e:QMessageBox.warning(self,'Check your settings',str(e));return
        self.player.pause();self.save_settings()
        self.begin_worker(self.job.export,self.finished_job,'Starting '+operation.replace('_',' ')+'…')

    def begin_worker(self,action,on_result,message):
        self.worker=Worker(action);self.worker.result.connect(on_result);self.worker.failure.connect(self.failed)
        self.worker.progress.connect(self.update_progress);self.worker.finished.connect(self.worker_done)
        self.tabs.setEnabled(False);[b.setEnabled(False) for b in self.buckets.values()]
        self.cancel.setEnabled(bool(self.job));self.status.setText(message);self.progress.setValue(0)
        self.worker.start()

    def update_progress(self,message,percent):
        self.status.setText(message);self.progress.setValue(percent)

    def worker_done(self):
        self.worker.deleteLater();self.worker=None;self.job=None
        self.tabs.setEnabled(True);[b.setEnabled(True) for b in self.buckets.values()];self.cancel.setEnabled(False)
        if self.closing:self.close()

    def finished_job(self,result):
        self.last_output=result['path'];self.progress.setValue(100)
        self.open_result.setEnabled(True);self.add_result.setEnabled(bool(result.get('media')))
        self.status.setText('Saved: '+Path(self.last_output).name)
        if 'segments' in result:
            self.word_segments=result['segments'];self.transcript_source=result['source'];self.srt.setPlainText(to_srt(self.word_segments))
            self.caption_source_label.setText('Subtitles for '+Path(self.transcript_source).name+' — correct below, then export.')
        self.statusBar().showMessage('Saved to '+self.last_output,30000)

    def failed(self,message):
        self.status.setText('Cancelled' if 'cancel' in message.lower() else 'Operation did not finish')
        QMessageBox.warning(self,'YouCutOwn Studio',message)

    def cancel_job(self):
        if self.job:self.job.cancel();self.status.setText('Cancelling… model loading may need a moment to return.')

    def preview_result(self):
        if not self.last_output:return
        if Path(self.last_output).suffix=='.srt':self.tabs.setCurrentIndex(3);return
        self.media[self.last_output]=probe(self.last_output);self.preview(self.last_output)

    def choose_output(self):
        path=QFileDialog.getExistingDirectory(self,'Save new files here',self.output_dir.text())
        if path:self.output_dir.setText(path)

    def import_srt(self):
        source=self.buckets['video'].chosen()
        if not source:QMessageBox.information(self,'Select video','Add and select the video these subtitles belong to first.');return
        path,_=QFileDialog.getOpenFileName(self,'Import subtitles','','SubRip subtitles (*.srt)')
        if path:
            try:
                text=Path(path).read_text(encoding='utf-8-sig');parse_srt(text)
                self.srt.setPlainText(text);self.word_segments=None;self.transcript_source=source
                self.caption_source_label.setText('Imported subtitles for '+Path(source).name)
            except Exception as e:QMessageBox.warning(self,'Cannot import subtitles',str(e))

    def save_srt(self):
        try:parse_srt(self.srt.toPlainText())
        except ValueError as e:QMessageBox.warning(self,'Check subtitles',str(e));return
        path,_=QFileDialog.getSaveFileName(self,'Save subtitles',str(Path(self.output_dir.text())/'subtitles.srt'),'SubRip subtitles (*.srt)')
        if path:Path(path).write_text(self.srt.toPlainText(),encoding='utf-8')

    def save_settings(self):
        values=dict(output_dir=self.output_dir.text(),size=self.output_size.currentText(),image_format=self.image_format.currentText())
        values.update({'last_dir_'+kind:bucket.directory for kind,bucket in self.buckets.items()})
        self.state_path.write_text(json.dumps(values,indent=2),encoding='utf-8')

    def save_project(self):
        if self.worker:return
        path,_=QFileDialog.getSaveFileName(self,'Save project',str(ROOT/'project.json'),'YouCutOwn Studio project (*.json)')
        if path:
            data=dict(version=1,buckets={k:b.paths() for k,b in self.buckets.items()},start=self.start.text(),end=self.end.text(),speed=self.speed.currentText(),
                      subtitles=self.srt.toPlainText(),transcript_source=self.transcript_source,word_segments=self.word_segments,
                      size=self.output_size.currentText(),fit=self.fit.currentText(),image_format=self.image_format.currentText(),transition=self.transition.currentText(),transition_duration=self.transition_duration.value(),
                      loop=self.loop.isChecked(),mix=self.mix.isChecked(),keep_audio=self.keep_audio.isChecked(),caption_style=self.caption_style.currentText(),
                      caption_position=self.caption_position.currentText(),font_size=self.font_size.value(),watermark=self.watermark.isChecked(),corner=self.corner.currentText())
            Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

    def load_project(self):
        if self.worker:return
        path,_=QFileDialog.getOpenFileName(self,'Open project',str(ROOT),'YouCutOwn Studio project (*.json)')
        if not path:return
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8'))
            files=[p for items in data['buckets'].values() for p in items]
            missing=[p for p in files if not Path(p).is_file()]
            if missing:raise ValueError('These source files have moved:\n'+'\n'.join(missing))
            self.clear_buckets();self.import_files(files)
            for name in ['start','end']:getattr(self,name).setText(data.get(name,''))
            for name in ['speed','size','fit','image_format','transition','caption_style','caption_position','corner']:
                if name in data:getattr(self,'output_size' if name=='size' else name).setCurrentText(str(data[name]))
            for name in ['transition_duration','font_size']:
                if name in data:getattr(self,name).setValue(data[name])
            for name in ['loop','mix','keep_audio','watermark']:
                if name in data:getattr(self,name).setChecked(data[name])
            self.srt.setPlainText(data.get('subtitles',''));self.transcript_source=data.get('transcript_source');self.word_segments=data.get('word_segments')
        except Exception as e:QMessageBox.warning(self,'Cannot open project',str(e))

    def clear_buckets(self):
        if self.worker:return
        self.player.stop();self.player.setSource(QUrl())
        for b in self.buckets.values():b.list.clear()

    def show_guide(self):
        dialog=QDialog(self);dialog.setWindowTitle('YouCutOwn Studio — guide');dialog.resize(820,700)
        layout=QVBoxLayout(dialog);browser=QTextBrowser();browser.setOpenExternalLinks(False)
        browser.setSource(QUrl.fromLocalFile(str(ROOT/'GUIDE.html')));layout.addWidget(browser)
        close=QPushButton('Close guide');close.clicked.connect(dialog.accept);layout.addWidget(close);dialog.exec()

    def closeEvent(self,event):
        if self.worker:
            if self.job and QMessageBox.question(self,'Export in progress','Cancel the operation and close?')==QMessageBox.StandardButton.Yes:
                self.closing=True;self.cancel_job()
            event.ignore();return
        self.save_settings();self.player.stop();event.accept()


STYLE='''
QWidget { font-family: Segoe UI; font-size: 12px; color: #17252e; }
QLabel, QCheckBox, QGroupBox { color: #17252e; }
QMainWindow { background: #f2f4f6; }
QTextBrowser { background: #ffffff; color: #17252e; border: 1px solid #cdd5dc; }
QLabel#title { font-size: 23px; font-weight: 650; color: #16383b; padding: 3px; }
QGroupBox { font-weight: 600; border: 1px solid #cdd5dc; border-radius: 5px; margin-top: 12px; padding: 10px 5px 5px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; }
QListWidget, QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: white; color: #17252e; border: 1px solid #b9c5cf; border-radius: 3px; padding: 4px; }
QPushButton { padding: 6px 10px; border: 1px solid #bbc7ce; border-radius: 4px; background: #fff; color: #192f38; }
QPushButton:hover { background: #e5f1f0; }
QPushButton:disabled { color: #89949b; background: #edf0f2; }
QPushButton#primary { background: #156963; color: white; font-weight: 600; }
QTabWidget::pane { background: #f8fafb; border: 1px solid #cdd5dc; }
QTabBar::tab { padding: 8px; color: #17252e; background: #e8edef; }
QTabBar::tab:selected { background: #ffffff; color: #103d3a; }
QProgressBar { min-height: 18px; border: 1px solid #cdd5dc; text-align: center; }
QProgressBar::chunk { background: #8cc6bf; }
'''
