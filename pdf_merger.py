from hello_pdf import PdfToolError, ensure_pdf_filename, get_existing_path, merge_pdfs


def main() -> None:
    try:
        total = int(input("How many PDFs do you want to merge?\n").strip())
        pdf_paths = []

        for index in range(total):
            raw_path = input(f"Enter the path of PDF {index + 1}: ")
            pdf_paths.append(get_existing_path(raw_path))

        output_name = ensure_pdf_filename(
            input("Output file name (press Enter for merged-pdf.pdf): "),
            "merged-pdf.pdf",
        )

        merge_pdfs(pdf_paths, output_name)
        print(f"Merged PDF created: {output_name}")
    except ValueError:
        print("Please enter a valid number.")
    except PdfToolError as error:
        print(error)


if __name__ == "__main__":
    main()
