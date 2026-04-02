from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image
from PyPDF2 import PdfMerger, PdfReader, PdfWriter


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


class PdfToolError(Exception):
    """Raised when the PDF utilities receive invalid input."""


def ensure_pdf_filename(name: str | None, fallback: str = "document.pdf") -> str:
    cleaned = (name or "").strip().strip('"')
    safe_name = Path(cleaned).name if cleaned else fallback

    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"

    return safe_name


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
