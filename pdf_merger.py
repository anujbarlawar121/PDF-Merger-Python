# have only file acess permission in the directory where this file is present

from PyPDF2 import PdfMerger

merger = PdfMerger()

pdfs = []
n = int(input("How many pdfs do you want to merge?\n"))

for i in range(0, n):
    pdf = input(f"Enter the name of pdf {i+1} : ")
    pdfs.append(pdf)   # fixed here

for pdf in pdfs:
    merger.append(pdf)

merger.write("merged-pdf.pdf")
merger.close()



# have folder acess permission in the directory where this file is present

# import os
# from PyPDF2 import PdfMerger

# # Path where your PDFs are stored
# base_path = r"C:\My Folder\Python_Project_CWH_123\Projects\pdf"

# merger = PdfMerger()
# pdfs = []
# n = int(input("How many pdfs do you want to merge?\n"))

# for i in range(n):
#     pdf_name = input(f"Enter the name of pdf {i+1} : ").strip().strip('"')
#     pdf_path = os.path.join(base_path, pdf_name)  # make full path
#     if not os.path.exists(pdf_path):
#         print("❌ File not found:", pdf_path)
#         exit(1)
#     pdfs.append(pdf_path)

# for pdf in pdfs:
#     merger.append(pdf)

# output_file = os.path.join(base_path, "merged-pdf.pdf")
# merger.write(output_file)
# merger.close()

# print("✅ Merged PDF created:", output_file)
