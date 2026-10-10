import requests
from datetime import date

BASE_URL = "http://127.0.0.1:8000"

def test_submit_report_form():
    payload = {
        "employee_id": 1,
        "key_tasks_completed": "Completed project X",
        "impact_outcome": "Improved efficiency by 20%",
        "challenges_faced": "Lack of resources",
        "support_required": "Additional team members",
        "tasks_planned_next_week": "Start project Y",
        "confidence_level": 4,
        "nothing_to_report_reason": None
    }
    response = requests.post(f"{BASE_URL}/reports/form", json=payload)
    
    print("\nRunning test_submit_report_form()")
    print("Status Code:", response.status_code)
    print("Response Body:", response.json())

    # Updated assertions to match the actual API response
    assert response.status_code == 200, "Report creation failed!"
    assert "message" in response.json(), "Response does not contain message!"
    assert "report_id" in response.json(), "Response does not contain report_id!"

    print("Report creation test passed!")

if __name__ == "__main__":
    test_submit_report_form()
