"""Check real image exports, lossless pixels, JPEG detail and source preservation."""
from pathlib import Path
import hashlib
import json
import sys

from PIL import Image, ImageChops, ImageStat, JpegImagePlugin

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from media_workbench.engine import ROOT, Job, Cancelled


def main():
    folder = ROOT / 'tests' / 'results' / 'image-formats'
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / 'Source odd size é.png'
    image = Image.new('RGBA', (257, 129))
    image.putdata([((x * 3) % 256, (y * 2) % 256, (x + y) % 256,
                    0 if x < 20 else 128 if x < 60 else 255)
                   for y in range(129) for x in range(257)])
    image.save(source)
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    results = []

    def export(image_format=None, **extra):
        spec = dict(operation='image', images=[str(source)], size='Original', output_dir=str(folder))
        if image_format:
            spec['image_format'] = image_format
        spec.update(extra)
        return Job(spec).export()

    for image_format, suffix in [('PNG', '.png'), ('WebP', '.webp')]:
        result = export(image_format)
        path = Path(result['path'])
        assert path.suffix == suffix and result['media']['kind'] == 'image'
        with Image.open(path) as actual:
            actual.load()
            assert actual.size == image.size
            assert actual.convert('RGBA').tobytes() == image.tobytes(), image_format
        results.append(f'{image_format}: exact RGBA pixels including hidden transparent colors; odd dimensions preserved')

    jpeg = export('JPEG')
    white = Image.new('RGB', image.size, 'white')
    white.paste(image, mask=image.getchannel('A'))
    with Image.open(jpeg['path']) as actual:
        actual.load()
        assert Path(jpeg['path']).suffix == '.jpg' and actual.format == 'JPEG'
        assert actual.size == image.size and actual.mode == 'RGB'
        assert JpegImagePlugin.get_sampling(actual) == 0, 'JPEG must retain full chroma resolution'
        error = sum(ImageStat.Stat(ImageChops.difference(actual, white)).mean) / 3
        assert error < 3, error
        assert min(actual.getpixel((5, 50))) > 250, 'Transparent pixels should render on white'
    results.append(f'JPEG: full chroma resolution, correct dimensions, white transparency background, mean error {error:.3f}/255')

    rgb_source = folder / 'Source RGB.bmp'
    image.convert('RGB').save(rgb_source)
    result = export('WebP', images=[str(rgb_source)])
    with Image.open(result['path']) as actual:
        assert actual.convert('RGB').tobytes() == image.convert('RGB').tobytes()
    results.append('RGB BMP to lossless WebP: exact RGB pixels')

    for fit in ['Fit', 'Fill / crop']:
        result = export('WebP', size='720p', fit=fit)
        with Image.open(result['path']) as actual:
            actual.load()
            assert actual.size == (1280, 720)
    results.append('Existing Fit and Fill resize choices export valid 1280x720 WebP files')
    assert Path(export()['path']).suffix == '.png'
    results.append('Older requests without a format still export PNG')

    try:
        export('invalid')
    except ValueError:
        results.append('Invalid format rejected')
    else:
        raise AssertionError('Invalid format accepted')
    cancelled = Job(dict(operation='image', images=[str(source)], image_format='WebP', output_dir=str(folder)))
    cancelled.cancel()
    try:
        cancelled.export()
    except Cancelled:
        assert not cancelled.output.exists()
        results.append('Cancellation creates no output')
    else:
        raise AssertionError('Cancellation ignored')
    assert not list(folder.glob('*.partial.*'))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    results.append('Source hash unchanged; no partial output files remain')
    (folder / 'verification.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    for result in results:
        print('PASS', result)
    print('COMPLETE', len(results), 'image conversion checks')


if __name__ == '__main__':
    main()
