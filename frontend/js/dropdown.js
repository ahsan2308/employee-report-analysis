/**
 * Searchable Dropdown Component
 * 
 * Creates an enhanced select dropdown with search filtering capability.
 * Usage: SearchableDropdown.enhance(selectElement);
 * For styling consistency without search: SearchableDropdown.enhanceSimple(selectElement);
 */
const SearchableDropdown = {
    /**
     * Enhance a standard select element with search functionality
     * @param {HTMLSelectElement} selectElement - The select element to enhance
     */
    enhance: function(selectElement) {
        if (!selectElement || selectElement.tagName !== 'SELECT') {
            console.error('SearchableDropdown requires a valid select element');
            return;
        }
        
        // Mark this select as searchable for styling purposes
        selectElement.setAttribute('data-searchable', 'true');
        
        // Create wrapper container
        const container = document.createElement('div');
        container.className = 'searchable-dropdown-container';
        
        // Insert the container before the select
        selectElement.parentNode.insertBefore(container, selectElement);
        
        // Move the select into the container
        container.appendChild(selectElement);
        
        // Create a custom dropdown header that includes search functionality
        const dropdownHeader = document.createElement('div');
        dropdownHeader.className = 'searchable-dropdown-header';
        dropdownHeader.tabIndex = 0; // Make it focusable
        
        // Create the custom dropdown UI
        const customDropdown = document.createElement('div');
        customDropdown.className = 'searchable-dropdown-popup';
        customDropdown.style.display = 'none';
        
        // Create search input
        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.className = 'searchable-dropdown-search';
        searchInput.placeholder = 'Type to search...';
        searchInput.autocomplete = 'off'; // Prevent browser autocomplete
        
        // Add search icon using Font Awesome
        const searchIcon = document.createElement('i');
        searchIcon.className = 'fas fa-search search-icon';
        
        // Create search wrapper for the popup
        const searchWrapper = document.createElement('div');
        searchWrapper.className = 'search-wrapper';
        searchWrapper.appendChild(searchIcon);
        searchWrapper.appendChild(searchInput);
        
        // Add the search wrapper to the dropdown
        customDropdown.appendChild(searchWrapper);
        
        // Add header and dropdown to container
        container.insertBefore(dropdownHeader, selectElement);
        container.appendChild(customDropdown);
        
        // Hide the original select
        selectElement.style.display = 'none';
        
        // Create and populate the options list
        const optionsList = document.createElement('ul');
        optionsList.className = 'searchable-options-list';
        customDropdown.appendChild(optionsList);
        
        // Function to update the selected text display
        const updateSelectedDisplay = () => {
            const selectedOption = selectElement.options[selectElement.selectedIndex];
            if (selectedOption && selectedOption.value) {
                dropdownHeader.setAttribute('data-value', selectedOption.text);
            } else {
                dropdownHeader.removeAttribute('data-value');
            }
        };
        
        // Initialize the header text
        updateSelectedDisplay();
        
        // Function to create and update dropdown options
        const updateOptions = () => {
            // Clear existing options
            optionsList.innerHTML = '';
            
            // Get search text
            const searchText = searchInput.value.toLowerCase();
            let hasResults = false;
            
            // Add options from select element
            Array.from(selectElement.options).forEach(option => {
                // Check if should be visible based on search
                if (!searchText || option.text.toLowerCase().includes(searchText)) {
                    hasResults = true;
                    const li = document.createElement('li');
                    li.dataset.value = option.value;
                    li.textContent = option.text;
                    
                    // Mark as selected if it's the currently selected option
                    if (option.selected) {
                        li.className = 'selected';
                    }
                    
                    // Add click handler to select this option
                    li.addEventListener('click', () => {
                        selectElement.value = option.value;
                        updateSelectedDisplay();
                        
                        // Trigger change event on the original select
                        selectElement.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        // Update visual selection
                        Array.from(optionsList.children).forEach(item => {
                            if (item.classList && !item.classList.contains('no-results')) {
                                item.className = item.dataset.value === option.value ? 'selected' : '';
                            }
                        });
                        
                        // Close the dropdown
                        closeDropdown();
                    });
                    
                    optionsList.appendChild(li);
                }
            });
            
            // Show "no results" message if needed
            if (!hasResults) {
                const emptyLi = document.createElement('li');
                emptyLi.className = 'no-results';
                emptyLi.textContent = 'No matching options';
                optionsList.appendChild(emptyLi);
            }
        };
        
        // Function to open the dropdown
        const openDropdown = () => {
            customDropdown.style.display = 'block';
            searchInput.focus();
            updateOptions();
            document.addEventListener('click', outsideClickHandler);
        };
        
        // Function to close the dropdown
        const closeDropdown = () => {
            customDropdown.style.display = 'none';
            searchInput.value = ''; // Clear search on close
            document.removeEventListener('click', outsideClickHandler);
        };
        
        // Handle clicks outside the dropdown
        const outsideClickHandler = (event) => {
            if (!container.contains(event.target)) {
                closeDropdown();
            }
        };
        
        // Toggle dropdown when clicking the header (entire area is clickable)
        dropdownHeader.addEventListener('click', (event) => {
            if (customDropdown.style.display === 'none') {
                openDropdown();
            } else {
                closeDropdown();
            }
        });
        
        // Update options when typing in search field
        searchInput.addEventListener('input', updateOptions);
        
        // Handle keyboard navigation
        searchInput.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                closeDropdown();
            } else if (event.key === 'Enter') {
                const firstOption = optionsList.querySelector('li:not(.no-results)');
                if (firstOption) {
                    firstOption.click();
                }
            }
        });
        
        // Update the dropdown when the select changes programmatically
        selectElement.addEventListener('change', updateSelectedDisplay);
        
        return {
            container,
            searchInput,
            select: selectElement,
            open: openDropdown,
            close: closeDropdown
        };
    },
    
    /**
     * Reset the search filter for a given dropdown
     * @param {HTMLSelectElement} selectElement - The enhanced select element
     */
    resetSearch: function(selectElement) {
        const container = selectElement.closest('.searchable-dropdown-container');
        if (!container) return;
        
        const searchInput = container.querySelector('.searchable-dropdown-search');
        if (searchInput) {
            searchInput.value = '';
            
            // If we have a custom dropdown, update its options
            const customDropdown = container.querySelector('.searchable-dropdown-popup');
            if (customDropdown && customDropdown.style.display === 'block') {
                // Find all options and make them visible again
                const optionsList = container.querySelector('.searchable-options-list');
                if (optionsList) {
                    Array.from(optionsList.children).forEach(li => {
                        if (li.classList && !li.classList.contains('no-results')) {
                            li.style.display = '';
                        }
                    });
                }
            }
        }
    },
    
    /**
     * Apply consistent styling to standard select elements (non-searchable)
     * Visual appearance matches searchable dropdown but without search functionality
     * @param {HTMLSelectElement} selectElement - The select element to style
     */
    enhanceSimple: function(selectElement) {
        if (!selectElement || selectElement.tagName !== 'SELECT') return;
        
        // Check if the dropdown is already enhanced
        const existingContainer = selectElement.closest('.searchable-dropdown-container');
        if (existingContainer) {
            // Just update the options without recreating the UI
            this.updateEnhancedDropdownOptions(selectElement, existingContainer);
            return selectElement;
        }
        
        // Create a container to wrap the select
        const container = document.createElement('div');
        container.className = 'searchable-dropdown-container';
        
        // Insert the container before the select
        selectElement.parentNode.insertBefore(container, selectElement);
        
        // Move the select into the container
        container.appendChild(selectElement);
        
        // Create a custom dropdown header
        const dropdownHeader = document.createElement('div');
        dropdownHeader.className = 'searchable-dropdown-header';
        dropdownHeader.tabIndex = 0;
        
        // Create the custom dropdown UI
        const customDropdown = document.createElement('div');
        customDropdown.className = 'searchable-dropdown-popup';
        customDropdown.style.display = 'none';
        
        // Add header and dropdown to container
        container.insertBefore(dropdownHeader, selectElement);
        container.appendChild(customDropdown);
        
        // Hide the original select
        selectElement.style.display = 'none';
        
        // Create and populate the options list
        const optionsList = document.createElement('ul');
        optionsList.className = 'searchable-options-list';
        customDropdown.appendChild(optionsList);
        
        // Function to update the selected text display
        function updateSelectedDisplay() {
            const selectedOption = selectElement.options[selectElement.selectedIndex];
            if (selectedOption && selectedOption.value) {
                dropdownHeader.setAttribute('data-value', selectedOption.text);
            } else {
                dropdownHeader.removeAttribute('data-value');
            }
        }
        
        // Initialize the header text
        updateSelectedDisplay();
        
        // Function to update options list
        function updateOptions() {
            // Clear existing options
            optionsList.innerHTML = '';
            
            // Add all options from select element
            Array.from(selectElement.options).forEach(option => {
                const li = document.createElement('li');
                li.dataset.value = option.value;
                li.textContent = option.text;
                
                // Mark as selected if it's the currently selected option
                if (option.selected) {
                    li.className = 'selected';
                }
                
                // Add click handler to select this option
                li.addEventListener('click', () => {
                    selectElement.value = option.value;
                    updateSelectedDisplay();
                    
                    // Trigger change event on the original select
                    selectElement.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    // Update visual selection
                    Array.from(optionsList.children).forEach(item => {
                        item.className = item.dataset.value === option.value ? 'selected' : '';
                    });
                    
                    // Close the dropdown
                    closeDropdown();
                });
                
                optionsList.appendChild(li);
            });
        }
        
        // Function to open the dropdown
        function openDropdown() {
            customDropdown.style.display = 'block';
            updateOptions();
            document.addEventListener('click', outsideClickHandler);
        }
        
        // Function to close the dropdown
        function closeDropdown() {
            customDropdown.style.display = 'none';
            document.removeEventListener('click', outsideClickHandler);
        }
        
        // Handle clicks outside the dropdown
        function outsideClickHandler(event) {
            if (!container.contains(event.target)) {
                closeDropdown();
            }
        }
        
        // Toggle dropdown when clicking the header
        dropdownHeader.addEventListener('click', (event) => {
            if (customDropdown.style.display === 'none') {
                openDropdown();
            } else {
                closeDropdown();
            }
        });
        
        // Update the dropdown when the select changes programmatically
        selectElement.addEventListener('change', updateSelectedDisplay);
        
        // Mark this select as not searchable but with consistent styling
        selectElement.setAttribute('data-consistent-style', 'true');
        
        return selectElement;
    },
    
    /**
     * Updates the options in an already enhanced dropdown without recreating the UI
     * @param {HTMLSelectElement} selectElement - The select element
     * @param {HTMLElement} container - The dropdown container
     */
    updateEnhancedDropdownOptions: function(selectElement, container) {
        const dropdownHeader = container.querySelector('.searchable-dropdown-header');
        const optionsList = container.querySelector('.searchable-options-list');
        
        if (!dropdownHeader || !optionsList) return;
        
        // Update header text
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        if (selectedOption && selectedOption.value) {
            dropdownHeader.setAttribute('data-value', selectedOption.text);
        } else {
            dropdownHeader.removeAttribute('data-value');
        }
        
        // Update options list
        optionsList.innerHTML = '';
        
        // Add all options from select element
        Array.from(selectElement.options).forEach(option => {
            const li = document.createElement('li');
            li.dataset.value = option.value;
            li.textContent = option.text;
            
            // Mark as selected if it's the currently selected option
            if (option.selected) {
                li.className = 'selected';
            }
            
            // Add click handler to select this option
            li.addEventListener('click', () => {
                selectElement.value = option.value;
                
                // Update header text
                if (option.value) {
                    dropdownHeader.setAttribute('data-value', option.text);
                } else {
                    dropdownHeader.removeAttribute('data-value');
                }
                
                // Trigger change event on the original select
                selectElement.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Update visual selection
                Array.from(optionsList.children).forEach(item => {
                    item.className = item.dataset.value === option.value ? 'selected' : '';
                });
                
                // Close the dropdown
                const customDropdown = container.querySelector('.searchable-dropdown-popup');
                if (customDropdown) {
                    customDropdown.style.display = 'none';
                }
            });
            
            optionsList.appendChild(li);
        });
    },
    
    /**
     * Destroy an enhanced dropdown and restore the original select
     * @param {HTMLSelectElement} selectElement - The enhanced select element
     */
    destroyEnhancement: function(selectElement) {
        const container = selectElement.closest('.searchable-dropdown-container');
        if (!container) return;
        
        // Get the parent element before removing container
        const parent = container.parentNode;
        
        // Move the select back to its original position
        selectElement.style.display = '';
        parent.insertBefore(selectElement, container);
        
        // Remove the container and all its children
        container.remove();
        
        // Reset data attributes
        selectElement.removeAttribute('data-consistent-style');
        selectElement.removeAttribute('data-searchable');
    }
};
