import requests
from datetime import date

BASE_URL = "http://127.0.0.1:8000"

def test_create_report():
    """Test creating a new report."""
    payload = {
        "employee_id": 1,
        "report_date": str(date.today()),  # Convert to string
        "report_text": "Completed database migration and optimized queries."
    }

    response = requests.post(f"{BASE_URL}/reports/", json=payload)
    
    print("\nRunning test_create_report()")
    print("Status Code:", response.status_code)
    print("Response Body:", response.json())

    assert response.status_code == 200, "Report creation failed!"
    assert "report" in response.json(), "Response does not contain report data!"
    assert response.json()["report"]["report_text"] == payload["report_text"], "Report text mismatch!"
    assert response.json()["report"]["employee_id"] == payload["employee_id"], "Employee ID mismatch!"

    print("Report creation test passed!")

if __name__ == "__main__":
    test_create_report()
