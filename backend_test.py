#!/usr/bin/env python3
"""
Backend API Test Suite for PDF to XLSX Converter
Tests all endpoints: GET /api/, POST /api/upload, GET /api/preview/{id}, GET /api/download/{id}
"""

import requests
import sys
from datetime import datetime
import io
import os

class PDFConverterAPITester:
    def __init__(self, base_url="https://excel-from-pdf-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.file_id = None

    def log_result(self, test_name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {test_name}")
        if details:
            print(f"    {details}")
        if success:
            self.tests_passed += 1
        print()

    def test_root_endpoint(self):
        """Test GET /api/ endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                expected_message = "PDF to XLSX Converter API"
                success = data.get("message") == expected_message
                details = f"Status: {response.status_code}, Message: {data.get('message', 'N/A')}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_result("Root API Endpoint", success, details)
            return success
        except Exception as e:
            self.log_result("Root API Endpoint", False, f"Error: {str(e)}")
            return False

    def create_test_pdf(self):
        """Create a minimal test PDF for upload"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            
            # Add some test data
            p.drawString(100, 750, "Test PDF for Conversion")
            p.drawString(100, 730, "Column1    Column2    Column3")
            p.drawString(100, 710, "Data1      Data2      Data3")
            p.drawString(100, 690, "Value1     Value2     Value3")
            
            p.save()
            buffer.seek(0)
            return buffer.getvalue()
        except ImportError:
            # Fallback: create a simple text file if reportlab not available
            return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000206 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n299\n%%EOF"

    def test_upload_pdf_invalid_file(self):
        """Test POST /api/upload with invalid file type"""
        try:
            # Test with a text file
            files = {'file': ('test.txt', b'This is not a PDF', 'text/plain')}
            response = requests.post(f"{self.api_url}/upload", files=files, timeout=30)
            
            success = response.status_code == 400
            details = f"Status: {response.status_code}"
            if response.status_code == 400:
                data = response.json()
                details += f", Error: {data.get('detail', 'N/A')}"
            
            self.log_result("Upload Invalid File Type", success, details)
            return success
        except Exception as e:
            self.log_result("Upload Invalid File Type", False, f"Error: {str(e)}")
            return False

    def test_upload_pdf_too_large(self):
        """Test POST /api/upload with file > 10MB"""
        try:
            # Create a large fake PDF
            large_content = b'%PDF-1.4\n' + b'A' * (11 * 1024 * 1024)  # 11MB
            files = {'file': ('large.pdf', large_content, 'application/pdf')}
            response = requests.post(f"{self.api_url}/upload", files=files, timeout=30)
            
            success = response.status_code == 400
            details = f"Status: {response.status_code}"
            if response.status_code == 400:
                data = response.json()
                details += f", Error: {data.get('detail', 'N/A')}"
            
            self.log_result("Upload Large File (>10MB)", success, details)
            return success
        except Exception as e:
            self.log_result("Upload Large File (>10MB)", False, f"Error: {str(e)}")
            return False

    def test_upload_valid_pdf(self):
        """Test POST /api/upload with valid PDF"""
        try:
            pdf_content = self.create_test_pdf()
            files = {'file': ('test.pdf', pdf_content, 'application/pdf')}
            response = requests.post(f"{self.api_url}/upload", files=files, timeout=30)
            
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                required_fields = ['id', 'original_filename', 'status', 'preview_data', 'total_rows', 'total_pages']
                
                for field in required_fields:
                    if field not in data:
                        success = False
                        details += f", Missing field: {field}"
                        break
                
                if success:
                    self.file_id = data.get('id')
                    details += f", ID: {self.file_id}, Rows: {data.get('total_rows')}, Pages: {data.get('total_pages')}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'N/A')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_result("Upload Valid PDF", success, details)
            return success
        except Exception as e:
            self.log_result("Upload Valid PDF", False, f"Error: {str(e)}")
            return False

    def test_get_preview(self):
        """Test GET /api/preview/{id}"""
        if not self.file_id:
            self.log_result("Get Preview", False, "No file ID available (upload may have failed)")
            return False
        
        try:
            response = requests.get(f"{self.api_url}/preview/{self.file_id}", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                required_fields = ['id', 'original_filename', 'status', 'preview_data', 'total_rows', 'total_pages']
                
                for field in required_fields:
                    if field not in data:
                        success = False
                        details += f", Missing field: {field}"
                        break
                
                if success:
                    details += f", Preview rows: {len(data.get('preview_data', []))}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'N/A')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_result("Get Preview", success, details)
            return success
        except Exception as e:
            self.log_result("Get Preview", False, f"Error: {str(e)}")
            return False

    def test_download_xlsx(self):
        """Test GET /api/download/{id}"""
        if not self.file_id:
            self.log_result("Download XLSX", False, "No file ID available (upload may have failed)")
            return False
        
        try:
            response = requests.get(f"{self.api_url}/download/{self.file_id}", timeout=30)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                content_type = response.headers.get('content-type', '')
                expected_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                
                if expected_type in content_type:
                    file_size = len(response.content)
                    details += f", Content-Type: {content_type}, Size: {file_size} bytes"
                else:
                    success = False
                    details += f", Wrong content type: {content_type}"
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'N/A')}"
                except:
                    details += f", Response: {response.text[:100]}"
            
            self.log_result("Download XLSX", success, details)
            return success
        except Exception as e:
            self.log_result("Download XLSX", False, f"Error: {str(e)}")
            return False

    def test_get_preview_not_found(self):
        """Test GET /api/preview/{id} with non-existent ID"""
        try:
            fake_id = "non-existent-id-12345"
            response = requests.get(f"{self.api_url}/preview/{fake_id}", timeout=10)
            
            success = response.status_code == 404
            details = f"Status: {response.status_code}"
            if response.status_code == 404:
                try:
                    data = response.json()
                    details += f", Error: {data.get('detail', 'N/A')}"
                except:
                    pass
            
            self.log_result("Preview Not Found", success, details)
            return success
        except Exception as e:
            self.log_result("Preview Not Found", False, f"Error: {str(e)}")
            return False

    def test_download_not_found(self):
        """Test GET /api/download/{id} with non-existent ID"""
        try:
            fake_id = "non-existent-id-12345"
            response = requests.get(f"{self.api_url}/download/{fake_id}", timeout=10)
            
            success = response.status_code == 404
            details = f"Status: {response.status_code}"
            if response.status_code == 404:
                try:
                    data = response.json()
                    details += f", Error: {data.get('detail', 'N/A')}"
                except:
                    pass
            
            self.log_result("Download Not Found", success, details)
            return success
        except Exception as e:
            self.log_result("Download Not Found", False, f"Error: {str(e)}")
            return False

    def cleanup(self):
        """Clean up uploaded files"""
        if self.file_id:
            try:
                response = requests.delete(f"{self.api_url}/file/{self.file_id}", timeout=10)
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                self.log_result("Cleanup Files", success, details)
            except Exception as e:
                self.log_result("Cleanup Files", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🧪 Starting PDF to XLSX Converter API Tests")
        print(f"📍 Testing endpoint: {self.base_url}")
        print("=" * 50)
        
        # Test basic connectivity
        self.test_root_endpoint()
        
        # Test error cases
        self.test_upload_pdf_invalid_file()
        self.test_upload_pdf_too_large()
        
        # Test valid upload and workflow
        upload_success = self.test_upload_valid_pdf()
        
        if upload_success:
            self.test_get_preview()
            self.test_download_xlsx()
        
        # Test not found cases
        self.test_get_preview_not_found()
        self.test_download_not_found()
        
        # Cleanup
        self.cleanup()
        
        # Summary
        print("=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"✨ Success Rate: {success_rate:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test runner"""
    tester = PDFConverterAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())