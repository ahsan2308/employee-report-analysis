import requests

BASE_URL = "http://127.0.0.1:8000"

def test_create_employee():
    """Test creating a new employee."""
    payload = {
        "name": "Test Employee",
        "wing": "Operations",
        "position": "Manager"
    }
    
    response = requests.post(f"{BASE_URL}/employees/", json=payload)
    
    print("\n Running test_create_employee()")
    print("Status Code:", response.status_code)
    print("Response Body:", response.json())

    assert response.status_code == 200, "Employee creation failed!"
    assert "employee" in response.json(), "Response does not contain employee data!"
    assert response.json()["employee"]["name"] == payload["name"], "Name mismatch!"
    assert response.json()["employee"]["wing"] == payload["wing"], "Wing mismatch!"
    assert response.json()["employee"]["position"] == payload["position"], "Position mismatch!"

    print("Employee creation test passed!")

def test_get_employees():
    """Test fetching all employees."""
    response = requests.get(f"{BASE_URL}/employees/")
    
    print("\nRunning test_get_employees()")
    print("Status Code:", response.status_code)
    print("Response Body:", response.json())

    assert response.status_code == 200, "Failed to fetch employees!"
    assert isinstance(response.json(), list), "Response is not a list!"
    assert len(response.json()) > 0, "No employees found!"

    print("Get employees test passed!")

if __name__ == "__main__":
    test_create_employee()
    test_get_employees()
