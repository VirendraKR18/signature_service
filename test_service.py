"""
Quick test script to verify signature service functionality
"""
import httpx
import sys
import time

SERVICE_URL = "http://localhost:8001"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    try:
        response = httpx.get(f"{SERVICE_URL}/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check passed")
            print(f"  Status: {data.get('status')}")
            print(f"  Signature detection available: {data.get('signature_detection', {}).get('available')}")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_root():
    """Test root endpoint"""
    print("\nTesting root endpoint...")
    try:
        response = httpx.get(f"{SERVICE_URL}/", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Root endpoint passed")
            print(f"  Service: {data.get('service')}")
            print(f"  Endpoints: {list(data.get('endpoints', {}).keys())}")
            return True
        else:
            print(f"✗ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Root endpoint failed: {e}")
        return False

def test_detect_with_sample(pdf_path):
    """Test detection with a sample PDF"""
    print(f"\nTesting detection with: {pdf_path}")
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path, f, 'application/pdf')}
            response = httpx.post(
                f"{SERVICE_URL}/detect/comprehensive",
                files=files,
                timeout=120.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Detection passed")
                print(f"  Status: {data.get('status')}")
                
                summary = data.get('summary', {})
                print(f"\n  Summary:")
                print(f"    Total signature fields: {summary.get('total_signature_fields', 0)}")
                print(f"    Filled fields: {summary.get('filled_fields', 0)}")
                print(f"    Empty fields: {summary.get('empty_fields', 0)}")
                print(f"    Electronic signatures: {summary.get('electronic_signatures', 0)}")
                print(f"    Handwritten signatures: {summary.get('handwritten_signatures', 0)}")
                
                if data.get('signature_fields'):
                    print(f"\n  Sample signature field:")
                    field = data['signature_fields'][0]
                    print(f"    Page: {field.get('page')}")
                    print(f"    Type: {field.get('field_type')}")
                    print(f"    Label: {field.get('label')}")
                    print(f"    Filled: {field.get('is_filled')}")
                
                return True
            else:
                print(f"✗ Detection failed: {response.status_code}")
                print(f"  Error: {response.text}")
                return False
    except FileNotFoundError:
        print(f"✗ PDF file not found: {pdf_path}")
        return False
    except Exception as e:
        print(f"✗ Detection failed: {e}")
        return False

def main():
    print("=" * 60)
    print("Signature Detection Service Test")
    print("=" * 60)
    
    print("\nWaiting for service to start...")
    time.sleep(2)
    
    results = []
    
    # Test health
    results.append(("Health Check", test_health()))
    
    # Test root
    results.append(("Root Endpoint", test_root()))
    
    # Test detection if PDF provided
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        results.append(("PDF Detection", test_detect_with_sample(pdf_path)))
    else:
        print("\nSkipping PDF detection test (no PDF file provided)")
        print("Usage: python test_service.py <path_to_pdf>")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
