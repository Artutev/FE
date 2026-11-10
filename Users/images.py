"""Приём и обработка загружаемых фото (обложки мероприятий, аватары).

- проверяем, что это действительно картинка (а не файл с расширением .jpg);
- поворачиваем по EXIF и полностью убираем метаданные (геолокация, модель телефона);
- уменьшаем и сохраняем в WebP — в 3–5 раз легче JPEG при том же качестве.
"""
import io
import uuid

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from Users.i18n import tr

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 40_000_000  # защита от «картинок-бомб»
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP', 'GIF', 'MPO'}

PRESETS = {
    # (макс. ширина, макс. высота, квадрат?)
    'cover': (1600, 1000, False),
    'avatar': (400, 400, True),
}


def _error(language, ru, en):
    return ValidationError(tr(language, ru, en))


def process_image(uploaded, kind, language='ru'):
    """Возвращает ContentFile (WebP) или бросает ValidationError с понятным текстом."""
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise _error(language, 'Фото больше 5 МБ. Выберите файл поменьше.', 'The photo is larger than 5 MB. Choose a smaller file.')

    data = uploaded.read()
    try:
        probe = Image.open(io.BytesIO(data))
        probe.verify()  # целостность файла
        image = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise _error(language, 'Это не похоже на картинку. Подойдут JPG, PNG или WebP.', "That doesn't look like an image. Use JPG, PNG or WebP.")

    if image.format not in ALLOWED_FORMATS:
        raise _error(language, 'Этот формат не поддерживается. Подойдут JPG, PNG или WebP.', 'This format is not supported. Use JPG, PNG or WebP.')
    if image.width * image.height > MAX_PIXELS:
        raise _error(language, 'Слишком большое разрешение фото.', 'The photo resolution is too large.')

    image = ImageOps.exif_transpose(image)  # «лежачие» фото с телефона
    has_alpha = image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info)
    image = image.convert('RGBA' if has_alpha else 'RGB')

    max_w, max_h, square = PRESETS[kind]
    if square:
        image = ImageOps.fit(image, (max_w, max_h), Image.LANCZOS, centering=(0.5, 0.4))
    else:
        image.thumbnail((max_w, max_h), Image.LANCZOS)

    out = io.BytesIO()
    image.save(out, 'WEBP', quality=82, method=6)  # без exif — метаданные не сохраняются
    return ContentFile(out.getvalue(), name=f'{uuid.uuid4().hex}.webp')


def replace_image(instance, field_name, new_file):
    """Ставит новый файл и удаляет старый с диска (или просто удаляет, если new_file=None)."""
    field = getattr(instance, field_name)
    old_name = field.name if field else ''
    if new_file is not None:
        field.save(new_file.name, new_file, save=False)
    else:
        setattr(instance, field_name, '')
    if old_name and old_name != getattr(instance, field_name).name:
        field.storage.delete(old_name)
