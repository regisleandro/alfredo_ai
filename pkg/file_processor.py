from PyPDF2 import PdfReader
import csv
import base64
import mimetypes
import tempfile
from PIL import Image
import pandas as pd
import os

class FileProcessor:
    def process_files(self, files):
        """Process uploaded files based on their type"""
        if not files:
            return None

        results = []
        image_contents = []

        for file in files:
            print(f"file: {file.get('name')}")
            filename = file.get('name')
            content = file.get('content')

            # Try to detect content type from base64 content
            content_type = None
            if isinstance(content, str) and content.startswith('data:'):
                # Handle data URL format
                content_type = content.split(';')[0].split(':')[1]
            elif isinstance(content, (str, bytes)):
                # Try to detect from content
                if isinstance(content, str):
                    try:
                        content = base64.b64decode(content)
                    except:
                        pass

                if isinstance(content, bytes):
                    # Check for common file signatures
                    if content.startswith(b'\x89PNG\r\n\x1a\n'):
                        content_type = 'image/png'
                    elif content.startswith(b'\xff\xd8\xff'):
                        content_type = 'image/jpeg'
                    elif content.startswith(b'%PDF-'):
                        content_type = 'application/pdf'
                    elif content.startswith(b'\x50\x4B\x03\x04'):  # ZIP file signature
                        content_type = 'application/zip'
                    elif content.startswith(b'\x25\x50\x44\x46'):  # PDF alternative signature
                        content_type = 'application/pdf'
                    elif content.startswith(b'RIFF') and content[8:12] == b'WEBP':
                        content_type = 'image/webp'
                    elif content.startswith(b'GIF87a') or content.startswith(b'GIF89a'):
                        content_type = 'image/gif'
                    elif content.startswith(b'BM'):  # BMP file signature
                        content_type = 'image/bmp'
                    elif content.startswith(b'II*\x00') or content.startswith(b'MM\x00*'):  # TIFF file signature
                        content_type = 'image/tiff'

            # Fallback to filename-based detection
            if not content_type:
                content_type = mimetypes.guess_type(filename)[0]
            # Additional fallback for image files
            if not content_type and filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff')):
                content_type = f'image/{filename.split(".")[-1].lower()}'

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                if isinstance(content, str):
                    try:
                        content = base64.b64decode(content)
                    except:
                        content = content.encode('utf-8')
                temp_file.write(content)
                file_path = temp_file.name

            try:
                if content_type == 'application/pdf':
                    text = self.extract_text_from_pdf(file_path)
                    results.append(f"=== PDF Content from {filename} ===\n{text}\n")

                elif content_type and content_type.startswith('image/'):
                    try:
                        # Try to open the image to verify it's valid
                        with Image.open(file_path) as img:
                            # Convert to RGB if necessary
                            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                                img = img.convert('RGB')

                            # Save the processed image
                            processed_path = f"{file_path}_processed.jpg"
                            img.save(processed_path, 'JPEG', quality=95)

                            # Read the processed image
                            with open(processed_path, 'rb') as img_file:
                                processed_content = img_file.read()

                            image_contents.append({
                                'type': 'image_url',
                                'image_url': {
                                    'url': f"data:image/jpeg;base64,{base64.b64encode(processed_content).decode('utf-8')}"
                                },
                                'filename': filename
                            })

                            # Clean up the processed image
                            os.unlink(processed_path)
                    except Exception as e:
                        print(f"Error processing image {filename}: {str(e)}")
                        results.append(f"Error processing image {filename}: {str(e)}")

                elif content_type == 'text/csv':
                    csv_data = self.extract_data_from_csv(file_path)
                    results.append(f"=== CSV Content from {filename} ===\n{csv_data}\n")

                else:
                    results.append(f"Unsupported file type for {filename}: {content_type or 'unknown'}")

            finally:
                os.unlink(file_path)

        if image_contents:
            return image_contents

        return "\n".join(results) if results else None

    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            return f"Error extracting text from PDF: {str(e)}"

    def extract_data_from_csv(self, file_path):
        """Extract data from CSV file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                rows = list(csv_reader)

                if rows:
                    df = pd.DataFrame(rows[1:], columns=rows[0])

                    if len(df) > 20:
                        summary = f"CSV contains {len(df)} rows and {len(df.columns)} columns.\n"
                        summary += f"Columns: {', '.join(df.columns)}\n"
                        summary += f"First 5 rows:\n{df.head(5).to_string()}\n"
                        summary += f"Last 5 rows:\n{df.tail(5).to_string()}"
                        return summary
                    else:
                        return df.to_string()

                return "Empty CSV file"
        except Exception as e:
            return f"Error processing CSV: {str(e)}"

    def prepare_image_for_vision_api(self, file_path):
        """Prepare image for vision API by encoding it as base64"""
        try:
            with open(file_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            print(f"Error preparing image: {str(e)}")
            return None
