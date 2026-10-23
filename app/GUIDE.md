# YouCutOwn Studio — everyday guide

## Start here

Double-click **windows.bat** in `your extracted YouCutOwn Studio folder`.
The app opens as a native desktop window. It does not launch a browser or server.
It needs no account, subscription, API key or internet connection. Python, FFmpeg,
Whisper models and Kokoro voices are included in this folder.

Nothing runs until you choose an action. Only one operation runs at a time.
Exports create new files; source videos, music and images are not overwritten.
The default destination is the app's **outputs** folder. You can change it using
**Browse…** beside **Save new files to**.

## Three buckets

- **Videos:** drop one or more clips here.
- **Audio / music:** drop soundtracks, voice recordings or other audio here.
- **Images / watermark:** drop photos, slideshow images or a logo here.

You can also use each bucket's **Add…** button. A mixed drop is sorted into the
appropriate buckets. The app references the originals; it does not upload or
duplicate them on import. Avoid moving a source file while using it.
Each file picker remembers its last used folder. On first use it starts in
Videos, Music or Pictures when that standard folder exists.

Click a row to select it. Single-file tools use that bucket's selected row.
**Join all videos**, **Make slideshow** and **Join all audio** use every item in
the relevant bucket, in its displayed order. Drag rows or use **↑ / ↓** to reorder.
**Remove** removes an item from the bucket; it does not delete the source file.

Click **Play / pause** below the preview. The scrubber seeks through the selected
audio/video. A still image shows a static preview. Preview support depends on the
input codec; a preview error does not necessarily prevent FFmpeg from exporting.

## Speed up a video, including 128× and 256×

1. Add and select the video.
2. Open **Trim / speed**.
3. Choose **Speed ×**, such as 2, 16, 64, 128 or 256. You may type a custom number.
4. Leave **End** blank to use the entire video, or set a range.
5. Click **Export trimmed / sped-up video**.

This changes the saved video's actual duration. A one-hour video becomes about
28 seconds at 128× or 14 seconds at 256×. Custom values range from 0.0625× to
4096×; the selected range must still produce at least one 30 FPS output frame.
The app exports 30 FPS by sampling/dropping/duplicating frames; it does not invent
motion-interpolated frames.

At 8× and above, **Keep original audio** switches off automatically. You may
switch it back on if wanted. Lower-speed audio processing preserves pitch.
Every time you change the speed, check the audio checkbox again.

## Trim a video

Select the video and use **Trim / speed**. Enter **Start** and **End** as seconds
(`12.5`) or a clock time (`00:01:12.5`). Blank End means the end of the video.
You can scrub the preview and click **Use playhead as start/end** instead.
Keep Speed at **1** for normal speed. Click **Export trimmed / sped-up video**.

To perform another operation on the edited result, click **Add result to bucket**
and select that new row. Each operation creates a separate finished file.

## Join videos with transitions

1. Put the clips in **Videos** and arrange their order.
2. Open **Join / slides**.
3. Choose **Between clips**: None, Crossfade, Fade through black, Wipe left,
   Slide left or Dissolve.
4. Set **Transition seconds** (0.5 is a useful start).
5. Choose an output size below the tabs. Use Fit to preserve the whole frame,
   or Fill / crop to fill the frame while cropping its edges.
6. Click **Join all videos**.

Mixed dimensions/frame rates are normalized automatically. Missing audio becomes
silence. A transition must be shorter than half of the shortest clip. Transitions
overlap adjacent clips, so two 3-second clips with a 0.5-second transition produce
about 5.5 seconds. This app renders joins rather than offering a stream-copy mode.

## Put music or narration over a video

Select a video in **Videos** and a soundtrack in **Audio / music**. Open **Music**.

- Keep **Loop video to match full music length** checked to repeat the video
  until the music ends. The final repetition is trimmed automatically.
- Uncheck it to keep the video's duration. Shorter music is padded with silence;
  longer music is trimmed.
- Leave **Mix with original sound** unchecked to replace the original sound.
- Check it to keep both. Adjust music/original volume; 1 is the original level.

Click **Export video with music**. This uses the selected video and selected
audio track, not every file in either bucket. To use several video clips, join
them first, then add/select the joined result before using Music.

## Automatic subtitles and styled captions

Finish trimming/speed changes first, then add/select the final edited video.

1. Open **Subtitles**.
2. Choose **base.en** for faster English transcription or **small** for
   multilingual recognition. Both are already downloaded and run on CPU.
3. Click **1 Transcribe selected video / audio**. If you last selected an audio
   row, it transcribes that audio instead; select the video row again for video.
4. Correct the text in the editor. Preserve its SRT structure and blank lines
   between entries. Press Enter for line breaks:

   ```text
   1
   00:00:00,100 --> 00:00:02,800
   These are my corrected words.
   ```

5. Choose **Highlight** for active-word color, **Outlined** for ordinary captions,
   or **Boxed** for a dark background. Set Bottom/Center/Top and font size.
6. Click **2 Export video with these subtitles**.

Transcription already saves an SRT and word-timing JSON in the output location.
**Save SRT…** saves your corrections separately. **Import SRT…** associates an
existing subtitle file with the currently selected video. Select that same video
when burning the subtitles. The app warns if the source does not match.

Word highlights use recognized word timings where unchanged. If you rewrite a
phrase or alter its time range, the new words are distributed across that subtitle
range. This is a reasonable approximation, not fresh speech alignment. Review it.
Recognition can make mistakes, especially with music/singing; correct before export.
Burned captions become part of the image and cannot be turned off in a player.

## Watermark

Add a logo image to **Images / watermark** and select its row. PNG with transparency
works well. Tick **Add selected image as watermark** below the tabs and choose a
corner. The logo is about 14% of the frame width with 80% opacity and a small margin.
It applies to video exports from Trim / speed, Join / slides, Music and Subtitles.
When captions use the same top/bottom edge, the logo is nudged away from that
caption band so the words remain readable. Tall logos are limited in height too.
Untick it when not wanted. To change logo size/opacity, prepare a suitable transparent
image before importing; this release uses fixed useful defaults.

## Kokoro voice

Open **Kokoro voice**, type narration, choose a voice and speaking speed, and click
**Generate voice WAV**. The local model uses no Piper or online voice service.
Click **Add result to bucket** when finished. You can then add the WAV to a video
using **Music**. That tab can mix narration with original sound or replace it.
Available voices include American and British male/female voices. Text limit is
12,000 characters per operation. Synthesis and speech-model loading may take a moment.

## Slideshow and extra tools

- **Join / slides → Make slideshow from all images:** ordered images, per-image
  duration, same transition controls. Add music afterward using Music.
- **Extra tools → Extract video audio:** selected video's audio becomes a WAV.
- **Join all audio:** join every audio row in order to WAV.
- **Normalize selected audio loudness:** make a separate WAV using an approximate
  -16 LUFS target; this release uses single-pass normalization.
- **Resize / convert image:** choose PNG, high-quality JPEG/JPG, or lossless WebP under Image file type, then export the selected image at the chosen output size.
- **Save video frame at trim start:** saves one PNG at the Start time in Trim / speed.

## Outputs, projects and performance

**Preview last result** previews the last audio/video/image or returns you to the
subtitle editor for SRT. **Add result to bucket** adds the generated media for
another operation. **Open folder** opens the destination in Explorer.

**Project → Save project…** saves source references, core editing settings and
the current subtitles to JSON. It does not embed/copy source media. Open it with
**Project → Open project…**. Keep the source files in place. Output folder/size
are remembered between app launches. Music levels, narration text and some tool
settings reset when reopening; the project file is not a full editing timeline.

**CPU quality** is the reliable starting encoder. **NVIDIA** uses the T1000's
hardware H.264 encoder for final video export; CPU filters and intermediate joins
still run on CPU. 1080p is a useful starting size; Original preserves the first or
selected input dimensions, rounded to even pixels. Vertical is 1080×1920; Square
is 1080×1080. Fit adds black bars; Fill / crop removes edges.

## Cancel or troubleshoot

Use **Cancel** to stop the current job. FFmpeg operations stop promptly; Whisper
and Kokoro may finish their current model-loading/inference step before responding.
Closing the app during an export asks whether to cancel. This release does not
resume interrupted renders; restart the operation.

- No speech found: try the multilingual model and check that the file has speech.
- Bad/missing preview: export a compatible MP4; an unsupported preview does not
  imply FFmpeg cannot read it.
- Transition error: reduce the transition duration or remove an extremely short clip.
- NVIDIA error: choose CPU quality and retry.
- Unsupported input: installed decoders determine support; unusual RAW/HEIC files
  may need conversion first. Animated images are treated as stills in slideshows.
- Missing file after reopening project: put the source back, or add it again.
- Detailed FFmpeg logs and frozen job requests are in **work**. Small logs are kept;
  temporary render media is removed at the end of a job. If Windows or the process
  was forcibly killed, a .partial.mp4 or intermediate may remain.
- Startup problems: launch `runtime\\python.exe app.py` from a terminal in the app
  folder to see errors; normal windowed-startup messages are in **logs/app.log**.

Keep the complete YouCutOwn Studio folder together. It does not need a separate build
folder, system Python packages, a browser, an account or internet during normal use.
