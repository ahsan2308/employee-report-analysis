document.addEventListener('DOMContentLoaded', function() {
    // Get elements
    const employeeForm = document.getElementById('employeeForm');
    const employeesTable = document.getElementById('employeesTable');
    const employeeList = document.getElementById('employeeList');
    const loadingEmployees = document.getElementById('loadingEmployees');
    const statusMessage = document.getElementById('statusMessage');
    
    // Load employees when page loads
    loadEmployees();
    
    // Add event listener for form submission
    employeeForm.addEventListener('submit', function(event) {
        event.preventDefault();
        
        // Get form data
        const employeeData = {
            name: document.getElementById('name').value,
            wing: document.getElementById('wing').value,
            position: document.getElementById('position').value
        };
        
        // Create employee
        createEmployee(employeeData);
    });
    
    // Load all employees from API
    async function loadEmployees() {
        try {
            // Show loading
            loadingEmployees.style.display = 'block';
            employeesTable.style.display = 'none';
            
            // Fetch employees
            const employees = await employeeApi.getAllEmployees();
            
            // Hide loading
            loadingEmployees.style.display = 'none';
            
            // If no employees, show message
            if (employees.length === 0) {
                employeeList.innerHTML = '<p>No employees found. Add an employee to get started.</p>';
                return;
            }
            
            // Populate table
            const tableBody = employeesTable.querySelector('tbody');
            tableBody.innerHTML = '';
            
            employees.forEach(employee => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${employee.id}</td>
                    <td>${employee.name}</td>
                    <td>${employee.wing}</td>
                    <td>${employee.position}</td>
                    <td>
                        <a href="reports.html?employee_id=${employee.id}" class="button">View Reports</a>
                    </td>
                `;
                tableBody.appendChild(row);
            });
            
            // Show table
            employeesTable.style.display = 'table';
            
        } catch (error) {
            // Handle errors
            loadingEmployees.style.display = 'none';
            showError('Error loading employees: ' + error.message);
        }
    }
    
    // Create a new employee
    async function createEmployee(employeeData) {
        try {
            // Show status
            showStatus('Adding employee...', 'loading');
            
            // Create employee
            const result = await employeeApi.createEmployee(employeeData);
            
            // Show success
            showSuccess('Employee added successfully!');
            
            // Clear form
            employeeForm.reset();
            
            // Reload employees
            loadEmployees();
            
        } catch (error) {
            // Handle errors
            showError('Error adding employee: ' + error.message);
        }
    }
    
    // Helper functions for UI messages
    function showError(message) {
        statusMessage.innerHTML = `<div class="error-message">${message}</div>`;
    }
    
    function showSuccess(message) {
        statusMessage.innerHTML = `<div class="success-message">${message}</div>`;
        // Clear message after 3 seconds
        setTimeout(() => {
            statusMessage.innerHTML = '';
        }, 3000);
    }
    
    function showStatus(message, type) {
        statusMessage.innerHTML = `<div class="${type}-message">${message}</div>`;
    }
});
