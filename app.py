from __future__ import annotations

from io import BytesIO
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from flask import (
    Flask,
    after_this_request,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.utils import secure_filename

from hello_pdf import (
    CONVERTIBLE_EXTENSIONS,
    PdfToolError,
    add_pages,
    convert_supported_file_to_pdf,
    delete_pages,
    ensure_download_filename,
    ensure_pdf_filename,
    extract_pages,
    generate_qr_code,
    get_pdf_page_count,
    images_to_pdf,
    merge_pdfs,
    parse_page_selection,
)


BASE_DIR = Path(__file__).resolve().parent
TMP_ROOT = Path(os.environ.get("PDF_ATELIER_TMP_DIR", tempfile.gettempdir())) / "pdf-atelier"
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
MAX_UPLOAD_SIZE = 64 * 1024 * 1024


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "classic-pdf-lounge")
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE

    TMP_ROOT.mkdir(parents=True, exist_ok=True)

    @app.get("/")
    def index():
        active_tool = request.args.get("tool", "merge")
        return render_template("index.html", active_tool=active_tool)

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    @app.post("/merge")
    def merge_route():
        try:
            uploads = [upload for upload in request.files.getlist("pdfs") if upload and upload.filename]
            if len(uploads) < 2:
                raise PdfToolError("Upload at least two PDF files to merge.")

            workspace = _make_workspace()
            saved_files = [_save_upload(upload, workspace, PDF_EXTENSIONS) for upload in uploads]
            output_name = ensure_pdf_filename(request.form.get("output_name"), "merged-classic.pdf")
            output_path = workspace / output_name
            merge_pdfs(saved_files, output_path)
            return _download_file(output_path, output_name)
        except PdfToolError as error:
            return _redirect_with_error("merge", str(error))
        except Exception as error:
            app.logger.exception("Merge PDFs failed: %s", error)
            return _redirect_with_error("merge", "Something went wrong while merging the PDFs.")

    @app.post("/delete-pages")
    def delete_pages_route():
        try:
            workspace = _make_workspace()
            pdf_upload = _require_upload(request.files.get("pdf"), PDF_EXTENSIONS, "a PDF to trim")
            pdf_path = _save_upload(pdf_upload, workspace, PDF_EXTENSIONS)
            page_count = get_pdf_page_count(pdf_path)
            pages_to_delete = parse_page_selection(request.form.get("pages", ""), page_count)
            output_name = ensure_pdf_filename(request.form.get("output_name"), "trimmed-classic.pdf")
            output_path = workspace / output_name
            delete_pages(pdf_path, pages_to_delete, output_path)
            return _download_file(output_path, output_name)
        except PdfToolError as error:
            return _redirect_with_error("delete", str(error))
        except Exception as error:
            app.logger.exception("Delete pages failed: %s", error)
            return _redirect_with_error("delete", "Something went wrong while deleting the pages.")

    @app.post("/extract-pages")
    def extract_pages_route():
        try:
            workspace = _make_workspace()
            pdf_upload = _require_upload(request.files.get("pdf"), PDF_EXTENSIONS, "a PDF to extract from")
            pdf_path = _save_upload(pdf_upload, workspace, PDF_EXTENSIONS)
            page_count = get_pdf_page_count(pdf_path)
            pages_to_extract = parse_page_selection(request.form.get("pages", ""), page_count)
            output_name = ensure_pdf_filename(request.form.get("output_name"), "extracted-classic.pdf")
            output_path = workspace / output_name
            extract_pages(pdf_path, pages_to_extract, output_path)
            return _download_file(output_path, output_name)
        except PdfToolError as error:
            return _redirect_with_error("extract", str(error))
        except Exception as error:
            app.logger.exception("Extract pages failed: %s", error)
            return _redirect_with_error("extract", "Something went wrong while extracting the pages.")

    @app.post("/add-pages")
    def add_pages_route():
        try:
            workspace = _make_workspace()
            base_upload = _require_upload(request.files.get("base_pdf"), PDF_EXTENSIONS, "a base PDF")
            extra_upload = _require_upload(request.files.get("extra_pdf"), PDF_EXTENSIONS, "a second PDF")
            base_path = _save_upload(base_upload, workspace, PDF_EXTENSIONS)
            extra_path = _save_upload(extra_upload, workspace, PDF_EXTENSIONS)
            output_name = ensure_pdf_filename(request.form.get("output_name"), "expanded-classic.pdf")
            output_path = workspace / output_name
            add_pages(base_path, extra_path, output_path)
            return _download_file(output_path, output_name)
        except PdfToolError as error:
            return _redirect_with_error("add", str(error))
        except Exception as error:
            app.logger.exception("Add pages failed: %s", error)
            return _redirect_with_error("add", "Something went wrong while adding the pages.")

    @app.post("/images-to-pdf")
    def images_to_pdf_route():
        try:
            uploads = [upload for upload in request.files.getlist("images") if upload and upload.filename]
            if not uploads:
                raise PdfToolError("Upload one or more images to convert.")

            workspace = _make_workspace()
            saved_images = [_save_upload(upload, workspace, IMAGE_EXTENSIONS) for upload in uploads]
            output_name = ensure_pdf_filename(request.form.get("output_name"), "gallery-classic.pdf")
            output_path = workspace / output_name
            images_to_pdf(saved_images, output_path)
            return _download_file(output_path, output_name)
        except PdfToolError as error:
            return _redirect_with_error("images", str(error))
        except Exception as error:
            app.logger.exception("Images to PDF failed: %s", error)
            return _redirect_with_error(
                "images",
                "Something went wrong while converting the images. Please try JPG or PNG files.",
            )

    @app.post("/qr-code")
    def qr_code_route():
        try:
            workspace = _make_workspace()
            qr_content = request.form.get("qr_text", "")
            output_format = (request.form.get("output_format") or "pdf").strip().lower()
            if output_format not in {"pdf", "png"}:
                raise PdfToolError("Choose PDF or PNG for the QR download format.")

            default_name = f"qr-classic.{output_format}"
            output_name = ensure_download_filename(
                request.form.get("output_name"),
                default_name,
                f".{output_format}",
            )
            output_path = workspace / output_name
            generate_qr_code(qr_content, output_path)
            return _download_file(
                output_path,
                output_name,
                mimetype="application/pdf" if output_format == "pdf" else "image/png",
            )
        except PdfToolError as error:
            return _redirect_with_error("qr", str(error))
        except Exception as error:
            app.logger.exception("Generate QR code failed: %s", error)
            return _redirect_with_error("qr", "Something went wrong while generating the QR code.")

    @app.post("/convert-file")
    def convert_file_route():
        try:
            workspace = _make_workspace()
            upload = _require_upload(
                request.files.get("source_file"),
                CONVERTIBLE_EXTENSIONS,
                "a supported file to convert",
            )
            source_path = _save_upload(upload, workspace, CONVERTIBLE_EXTENSIONS)
            output_name = ensure_pdf_filename(request.form.get("output_name"), "converted-classic.pdf")
            output_path = workspace / output_name
            convert_supported_file_to_pdf(source_path, output_path)
            return _download_file(output_path, output_name)
        except PdfToolError as error:
            return _redirect_with_error("convert", str(error))
        except Exception as error:
            app.logger.exception("Convert file failed: %s", error)
            return _redirect_with_error(
                "convert",
                "Something went wrong while converting the file. Try an image, TXT, MD, CSV, or JSON file.",
            )

    @app.errorhandler(413)
    def request_entity_too_large(_error):
        flash("The upload is too large. Keep the total request under 64 MB.", "error")
        return redirect(url_for("index"))

    return app


def _make_workspace() -> Path:
    workspace = Path(tempfile.mkdtemp(prefix="classic-pdf-", dir=TMP_ROOT))

    @after_this_request
    def cleanup(response):
        shutil.rmtree(workspace, ignore_errors=True)
        return response

    return workspace


def _require_upload(upload, allowed_extensions: set[str], label: str):
    if upload is None or not upload.filename:
        raise PdfToolError(f"Please choose {label}.")

    suffix = Path(upload.filename).suffix.lower()
    if suffix not in allowed_extensions:
        allowed_list = ", ".join(sorted(allowed_extensions))
        raise PdfToolError(f"{upload.filename} is not supported. Allowed types: {allowed_list}.")

    return upload


def _save_upload(upload, workspace: Path, allowed_extensions: set[str]) -> Path:
    _require_upload(upload, allowed_extensions, "a file")
    cleaned_name = secure_filename(upload.filename) or f"upload-{uuid.uuid4().hex}"
    destination = workspace / f"{uuid.uuid4().hex[:10]}-{cleaned_name}"
    upload.save(destination)
    return destination


def _download_file(path: Path, download_name: str, mimetype: str = "application/pdf"):
    return send_file(
        BytesIO(path.read_bytes()),
        as_attachment=True,
        download_name=download_name,
        mimetype=mimetype,
    )


def _redirect_with_error(tool: str, message: str):
    flash(message, "error")
    return redirect(url_for("index", tool=tool))


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
