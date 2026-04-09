from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import qrcode


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".log",
    ".py",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".xml",
}
CONVERTIBLE_EXTENSIONS = IMAGE_EXTENSIONS | TEXT_EXTENSIONS
PAGE_SIZE = (1240, 1754)
PAGE_MARGIN_X = 92
PAGE_MARGIN_Y = 88
TEXT_FILE_SIZE_LIMIT = 512 * 1024


class PdfToolError(Exception):
    """Raised when the PDF utilities receive invalid input."""


def ensure_download_filename(
    name: str | None,
    fallback: str,
    required_extension: str,
) -> str:
    cleaned = (name or "").strip().strip('"')
    safe_name = Path(cleaned).name if cleaned else fallback

    if not safe_name:
        safe_name = fallback

    required_extension = required_extension.lower()
    if Path(safe_name).suffix.lower() != required_extension:
        stem = Path(safe_name).stem or Path(fallback).stem or "download"
        safe_name = f"{stem}{required_extension}"

    return safe_name


def ensure_pdf_filename(name: str | None, fallback: str = "document.pdf") -> str:
    return ensure_download_filename(name, fallback, ".pdf")


def get_existing_path(raw_path: str) -> Path:
    path = Path(raw_path.strip().strip('"')).expanduser()
    if not path.exists():
        raise PdfToolError(f"File not found: {path}")
    return path


def get_pdf_page_count(pdf_path: str | Path) -> int:
    reader = PdfReader(str(pdf_path))
    return len(reader.pages)


def parse_page_selection(selection: str, total_pages: int) -> list[int]:
    if not selection or not selection.strip():
        raise PdfToolError("Please enter one or more page numbers.")

    ordered_pages: list[int] = []
    seen_pages: set[int] = set()

    for raw_token in selection.replace(",", " ").split():
        token = raw_token.strip()
        if not token:
            continue

        if "-" in token:
            start_text, end_text = token.split("-", 1)
            if not start_text.isdigit() or not end_text.isdigit():
                raise PdfToolError(f"Invalid page range: {token}")

            start, end = int(start_text), int(end_text)
            if start > end:
                raise PdfToolError(f"Page range must be ascending: {token}")

            page_numbers = range(start, end + 1)
        else:
            if not token.isdigit():
                raise PdfToolError(f"Invalid page number: {token}")
            page_numbers = [int(token)]

        for page_number in page_numbers:
            if page_number < 1 or page_number > total_pages:
                raise PdfToolError(
                    f"Page {page_number} is outside the document range of 1-{total_pages}."
                )
            if page_number not in seen_pages:
                ordered_pages.append(page_number)
                seen_pages.add(page_number)

    if not ordered_pages:
        raise PdfToolError("No valid pages were selected.")

    return ordered_pages


def merge_pdfs(pdf_paths: Iterable[str | Path], output_path: str | Path) -> Path:
    paths = [Path(path) for path in pdf_paths]
    if len(paths) < 2:
        raise PdfToolError("Choose at least two PDF files to merge.")

    merger = PdfMerger()
    try:
        for pdf_path in paths:
            merger.append(str(pdf_path))

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        merger.write(str(output))
        return output
    finally:
        merger.close()


def delete_pages(pdf_path: str | Path, pages_to_delete: Iterable[int], output_path: str | Path) -> Path:
    delete_set = set(pages_to_delete)
    if not delete_set:
        raise PdfToolError("Pick at least one page to remove.")

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    if len(delete_set) >= len(reader.pages):
        raise PdfToolError("Deleting every page would leave an empty PDF.")

    for index, page in enumerate(reader.pages, start=1):
        if index not in delete_set:
            writer.add_page(page)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)

    return output


def extract_pages(pdf_path: str | Path, pages_to_extract: Iterable[int], output_path: str | Path) -> Path:
    selected_pages = list(pages_to_extract)
    if not selected_pages:
        raise PdfToolError("Pick at least one page to extract.")

    reader = PdfReader(str(pdf_path))
    writer = PdfWriter()

    for page_number in selected_pages:
        writer.add_page(reader.pages[page_number - 1])

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)

    return output


def add_pages(base_pdf_path: str | Path, extra_pdf_path: str | Path, output_path: str | Path) -> Path:
    reader_base = PdfReader(str(base_pdf_path))
    reader_extra = PdfReader(str(extra_pdf_path))
    writer = PdfWriter()

    for page in reader_base.pages:
        writer.add_page(page)

    for page in reader_extra.pages:
        writer.add_page(page)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)

    return output


def images_to_pdf(image_paths: Iterable[str | Path], output_path: str | Path) -> Path:
    paths = [Path(path) for path in image_paths]
    if not paths:
        raise PdfToolError("Choose at least one image to convert.")

    prepared_images: list[Image.Image] = []

    try:
        for image_path in paths:
            if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
                raise PdfToolError(f"Unsupported image format: {image_path.name}")

            with Image.open(image_path) as source_image:
                rgba_image = source_image.convert("RGBA")
                background = Image.new("RGBA", rgba_image.size, "white")
                background.alpha_composite(rgba_image)
                prepared_images.append(background.convert("RGB"))

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        prepared_images[0].save(
            output,
            save_all=True,
            append_images=prepared_images[1:],
        )
        return output
    finally:
        for prepared_image in prepared_images:
            prepared_image.close()


def generate_qr_code(data: str, output_path: str | Path) -> Path:
    content = data.strip()
    if not content:
        raise PdfToolError("Enter text or a URL to turn into a QR code.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)

    qr_image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    try:
        if output.suffix.lower() == ".png":
            qr_image.save(output, format="PNG")
            return output

        if output.suffix.lower() != ".pdf":
            raise PdfToolError("QR downloads currently support only PDF or PNG.")

        sheet = Image.new("RGB", PAGE_SIZE, "white")
        draw = ImageDraw.Draw(sheet)
        title_font = _load_font(42)
        subtitle_font = _load_font(22)
        body_font = _load_font(24)

        draw.text((PAGE_MARGIN_X, 120), "QR Code Sheet", fill=(32, 45, 60), font=title_font)
        draw.text(
            (PAGE_MARGIN_X, 188),
            "Scan this code or share the text below.",
            fill=(87, 73, 57),
            font=subtitle_font,
        )

        qr_copy = qr_image.copy()
        qr_copy.thumbnail((760, 760))
        qr_x = (PAGE_SIZE[0] - qr_copy.width) // 2
        qr_y = 300
        sheet.paste(qr_copy, (qr_x, qr_y))

        footer_top = qr_y + qr_copy.height + 72
        wrapped_lines = _wrap_text_block(content, body_font, PAGE_SIZE[0] - (PAGE_MARGIN_X * 2))
        if len(wrapped_lines) > 6:
            wrapped_lines = wrapped_lines[:5] + ["..."]

        draw.text((PAGE_MARGIN_X, footer_top), "Encoded text", fill=(137, 72, 59), font=subtitle_font)
        line_height = _line_height(body_font, 10)
        text_y = footer_top + 42
        for line in wrapped_lines:
            draw.text((PAGE_MARGIN_X, text_y), line, fill=(32, 45, 60), font=body_font)
            text_y += line_height

        sheet.save(output, "PDF", resolution=150.0)
        qr_copy.close()
        sheet.close()
        return output
    finally:
        qr_image.close()


def convert_supported_file_to_pdf(source_path: str | Path, output_path: str | Path) -> Path:
    source = Path(source_path)
    suffix = source.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        return images_to_pdf([source], output_path)

    if suffix in TEXT_EXTENSIONS:
        return text_to_pdf(source, output_path)

    raise PdfToolError(
        "This converter supports common image files and text-like files such as TXT, MD, CSV, and JSON."
    )


def text_to_pdf(source_path: str | Path, output_path: str | Path) -> Path:
    source = Path(source_path)
    content = _read_text_file(source)
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4)
    logical_lines = normalized.split("\n")

    body_font = _load_font(24)
    title_font = _load_font(34)
    subtitle_font = _load_font(20)
    page_width, page_height = PAGE_SIZE
    usable_width = page_width - (PAGE_MARGIN_X * 2)
    line_height = _line_height(body_font, 10)
    header_height = _line_height(title_font, 16) + _line_height(subtitle_font, 8) + 14
    footer_height = _line_height(subtitle_font, 0) + 10
    lines_per_page = max(1, (page_height - (PAGE_MARGIN_Y * 2) - header_height - footer_height) // line_height)

    wrapped_lines: list[str] = []
    for logical_line in logical_lines:
        wrapped_lines.extend(_wrap_text_block(logical_line, body_font, usable_width))

    if not wrapped_lines:
        wrapped_lines = ["[This file is empty.]"]

    pages: list[Image.Image] = []
    try:
        total_pages = max(1, (len(wrapped_lines) + lines_per_page - 1) // lines_per_page)
        for page_index in range(total_pages):
            page = Image.new("RGB", PAGE_SIZE, "white")
            draw = ImageDraw.Draw(page)

            draw.text((PAGE_MARGIN_X, PAGE_MARGIN_Y), source.name, fill=(32, 45, 60), font=title_font)
            draw.text(
                (PAGE_MARGIN_X, PAGE_MARGIN_Y + _line_height(title_font, 16)),
                f"Converted into PDF from a supported text file",
                fill=(87, 73, 57),
                font=subtitle_font,
            )

            draw.line(
                (
                    PAGE_MARGIN_X,
                    PAGE_MARGIN_Y + header_height - 8,
                    page_width - PAGE_MARGIN_X,
                    PAGE_MARGIN_Y + header_height - 8,
                ),
                fill=(212, 198, 171),
                width=2,
            )

            start = page_index * lines_per_page
            end = start + lines_per_page
            text_y = PAGE_MARGIN_Y + header_height + 10
            for line in wrapped_lines[start:end]:
                draw.text((PAGE_MARGIN_X, text_y), line, fill=(32, 45, 60), font=body_font)
                text_y += line_height

            footer_label = f"Page {page_index + 1} of {total_pages}"
            footer_width = _text_width(footer_label, subtitle_font)
            draw.text(
                (page_width - PAGE_MARGIN_X - footer_width, page_height - PAGE_MARGIN_Y),
                footer_label,
                fill=(87, 73, 57),
                font=subtitle_font,
            )

            pages.append(page)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        pages[0].save(output, "PDF", save_all=True, append_images=pages[1:], resolution=150.0)
        return output
    finally:
        for page in pages:
            page.close()


def _read_text_file(path: Path) -> str:
    raw_bytes = path.read_bytes()
    if len(raw_bytes) > TEXT_FILE_SIZE_LIMIT:
        raise PdfToolError("Text conversion works best for files up to 512 KB.")

    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

        if "\x00" in text:
            continue
        return text

    raise PdfToolError("This file does not look like readable text.")


def _load_font(size: int) -> ImageFont.ImageFont:
    for font_name in (
        "DejaVuSansMono.ttf",
        "DejaVuSans.ttf",
        "LiberationMono-Regular.ttf",
        "LiberationSans-Regular.ttf",
        "arial.ttf",
    ):
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue

    return ImageFont.load_default()


def _line_height(font: ImageFont.ImageFont, padding: int) -> int:
    bbox = font.getbbox("Ag")
    return (bbox[3] - bbox[1]) + padding


def _text_width(text: str, font: ImageFont.ImageFont) -> int:
    if not text:
        return 0

    bbox = font.getbbox(text)
    return bbox[2] - bbox[0]


def _wrap_text_block(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    if text == "":
        return [""]

    if _text_width(text, font) <= max_width:
        return [text]

    wrapped: list[str] = []
    start = 0
    while start < len(text):
        end = start
        last_break = None

        while end < len(text):
            candidate = text[start : end + 1]
            if _text_width(candidate, font) <= max_width:
                if text[end].isspace():
                    last_break = end
                end += 1
                continue
            break

        if end >= len(text):
            wrapped.append(text[start:].rstrip())
            break

        split_at = last_break + 1 if last_break is not None and last_break >= start else end
        segment = text[start:split_at].rstrip()
        if not segment:
            segment = text[start:end].rstrip() or text[start:end]

        wrapped.append(segment)
        start = split_at
        while start < len(text) and text[start].isspace():
            start += 1

    return wrapped or [text]


def _prompt_path(message: str) -> Path:
    return get_existing_path(input(message))


def _prompt_output_name(message: str, fallback: str) -> str:
    return ensure_pdf_filename(input(message), fallback)


def merge_pdfs_cli() -> None:
    total = int(input("How many PDFs to merge? ").strip())
    pdf_paths = [_prompt_path(f"Enter PDF {index + 1} path: ") for index in range(total)]
    output_name = _prompt_output_name("Output file name: ", "merged-classic.pdf")
    merge_pdfs(pdf_paths, output_name)
    print(f"PDFs merged successfully into {output_name}")


def delete_pages_cli() -> None:
    pdf_path = _prompt_path("Enter PDF file: ")
    total_pages = get_pdf_page_count(pdf_path)
    print(f"Total pages: {total_pages}")
    pages = parse_page_selection(input("Pages to delete (example: 1, 3-4): "), total_pages)
    output_name = _prompt_output_name("Output file name: ", "trimmed-document.pdf")
    delete_pages(pdf_path, pages, output_name)
    print(f"Pages deleted successfully into {output_name}")


def extract_pages_cli() -> None:
    pdf_path = _prompt_path("Enter PDF file: ")
    total_pages = get_pdf_page_count(pdf_path)
    pages = parse_page_selection(input("Pages to extract (example: 2, 5-6): "), total_pages)
    output_name = _prompt_output_name("Output file name: ", "extracted-pages.pdf")
    extract_pages(pdf_path, pages, output_name)
    print(f"Pages extracted successfully into {output_name}")


def add_pages_cli() -> None:
    base_pdf = _prompt_path("Enter base PDF: ")
    extra_pdf = _prompt_path("Enter PDF to add pages from: ")
    output_name = _prompt_output_name("Output file name: ", "expanded-document.pdf")
    add_pages(base_pdf, extra_pdf, output_name)
    print(f"Pages added successfully into {output_name}")


def image_to_pdf_cli() -> None:
    total = int(input("How many images? ").strip())
    image_paths = [_prompt_path(f"Enter image {index + 1} path: ") for index in range(total)]
    output_name = _prompt_output_name("Output PDF name: ", "gallery-export.pdf")
    images_to_pdf(image_paths, output_name)
    print(f"Images converted successfully into {output_name}")


def main() -> None:
    actions = {
        "1": merge_pdfs_cli,
        "2": delete_pages_cli,
        "3": extract_pages_cli,
        "4": add_pages_cli,
        "5": image_to_pdf_cli,
    }

    while True:
        print("\nCLASSIC PDF TOOL")
        print("1. Merge PDFs")
        print("2. Delete Pages")
        print("3. Extract Pages")
        print("4. Add Pages to PDF")
        print("5. Image to PDF")
        print("6. Exit")

        choice = input("Enter choice: ").strip()

        if choice == "6":
            print("Exiting...")
            break

        action = actions.get(choice)
        if action is None:
            print("Invalid choice")
            continue

        try:
            action()
        except PdfToolError as error:
            print(error)
        except ValueError:
            print("Please enter a valid number.")


if __name__ == "__main__":
    main()
