import fitz  # PyMuPDF
import os

def write_bytes_to_file(byte_data, output_filename):
    # Open the file in write-binary mode ('wb')
    with open(output_filename, 'wb') as file:
        # Write the byte data to the file
        file.write(byte_data)

def read_bytes_from_file(file_path):
    # Open the file in read-binary mode ('rb')
    with open(file_path, 'rb') as file:
        # Read the entire content of the file as bytes
        byte_data = file.read()
    
    return byte_data

# Function to convert PDF to images
def convert_pdf_file_to_image_files(pdf_path, output_folder="output_images"):
    # Open the PDF file
    pdf_document = fitz.open(pdf_path)

    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Iterate through each page of the PDF
    images = []
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)  # Load page
        
        # Convert the page to a pixmap (image)
        pixmap = page.get_pixmap()

        # Save the pixmap as an image file (e.g., PNG)
        output_image_path = os.path.join(output_folder, f"page_{page_num + 1}.png")
        pixmap.save(output_image_path)
        print(f"Page {page_num + 1} saved as {output_image_path}")
        images.append(output_image_path)
    return images

def convert_pdf_to_images(pdf_data):
    temp = 'temp.pdf'
    write_bytes_to_file(pdf_data, temp)
    images = convert_pdf_file_to_image_files(temp)
    content = []
    for i in images:
       content.append(read_bytes_from_file(i))
       os.remove(i)
    os.remove(temp)
    return content
