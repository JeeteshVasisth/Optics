class OpticsCalculator {
    constructor() {
        this.form = document.getElementById('opticsForm');
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Form submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.calculateOptics();
        });

        // Input validation
        const inputs = this.form.querySelectorAll('input[type="number"]');
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                this.validateInput(input);
            });
        });

        // Optic type change
        const opticTypeInputs = this.form.querySelectorAll('input[name="optic_type"]');
        opticTypeInputs.forEach(input => {
            input.addEventListener('change', () => {
                this.updateFormLabels();
            });
        });

        // Shape change
        const shapeInputs = this.form.querySelectorAll('input[name="shape"]');
        shapeInputs.forEach(input => {
            input.addEventListener('change', () => {
                this.updateFormLabels();
            });
        });

        // Initial label update
        this.updateFormLabels();
    }

    validateInput(input) {
        const value = parseFloat(input.value);
        const inputId = input.id;
        
        // Remove previous validation classes
        input.classList.remove('is-valid', 'is-invalid');
        
        if (input.value.trim() === '') {
            return; // Empty is allowed
        }

        if (isNaN(value)) {
            input.classList.add('is-invalid');
            return;
        }

        // Specific validations based on input type
        let isValid = true;
        
        if (inputId === 'u' && value >= 0) {
            isValid = false;
        } else if (inputId === 'h1' && value <= 0) {
            isValid = false;
        } else if (inputId === 'focal_length' && value === 0) {
            isValid = false;
        }

        input.classList.add(isValid ? 'is-valid' : 'is-invalid');
    }

    updateFormLabels() {
        const opticType = this.form.querySelector('input[name="optic_type"]:checked').value;
        const shape = this.form.querySelector('input[name="shape"]:checked').value;
        
        // Update help text based on selections
        const helpText = this.getHelpText(opticType, shape);
        // Could add dynamic help updates here
    }

    getHelpText(opticType, shape) {
        const conventions = {
            mirror: {
                concave: "Concave mirrors: f > 0, can form real or virtual images",
                convex: "Convex mirrors: f > 0, always form virtual, erect, diminished images"
            },
            lens: {
                convex: "Convex lenses: f > 0, can form real or virtual images",
                concave: "Concave lenses: f < 0, always form virtual, erect, diminished images"
            }
        };
        
        return conventions[opticType]?.[shape] || "";
    }

    async calculateOptics() {
        // Show loading indicator
        this.showLoading(true);
        this.hideResults();

        // Collect form data
        const formData = new FormData(this.form);
        const data = {
            optic_type: formData.get('optic_type'),
            shape: formData.get('shape')
        };

        // Add numerical inputs
        const inputs = ['focal_length', 'u', 'v', 'h1', 'h2'];
        inputs.forEach(input => {
            const value = formData.get(input);
            if (value && value.trim() !== '') {
                data[input] = parseFloat(value);
            }
        });

        try {
            const response = await fetch('/calculate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (result.success) {
                this.displayResults(result);
            } else {
                this.displayErrors(result.errors);
            }
        } catch (error) {
            console.error('Calculation error:', error);
            this.displayErrors(['Network error: Please check your connection and try again.']);
        } finally {
            this.showLoading(false);
        }
    }

    displayResults(result) {
        this.hideErrors();
        
        // Display calculated values
        this.populateResultsGrid(result.results);
        
        // Display image characteristics if available
        if (result.image_characteristics) {
            this.displayImageCharacteristics(result.image_characteristics);
        }
        
        // Display ray diagram
        if (result.diagram) {
            this.displayRayDiagram(result.diagram);
        }
        
        // Display warnings if any
        if (result.warnings && result.warnings.length > 0) {
            this.displayWarnings(result.warnings);
        }
        
        // Show results card
        document.getElementById('resultsCard').classList.remove('d-none');
        document.getElementById('diagramCard').classList.remove('d-none');
    }

    populateResultsGrid(results) {
        const grid = document.getElementById('resultsGrid');
        grid.innerHTML = '';

        const labels = {
            focal_length: { icon: 'fa-crosshairs', label: 'Focal Length (f)', unit: 'cm' },
            u: { icon: 'fa-arrow-left', label: 'Object Distance (u)', unit: 'cm' },
            v: { icon: 'fa-arrow-right', label: 'Image Distance (v)', unit: 'cm' },
            h1: { icon: 'fa-arrows-alt-v', label: 'Object Height (h₁)', unit: 'cm' },
            h2: { icon: 'fa-arrows-alt-v', label: 'Image Height (h₂)', unit: 'cm' }
        };

        for (const [key, value] of Object.entries(results)) {
            if (value !== null && value !== undefined) {
                const config = labels[key];
                const col = document.createElement('div');
                col.className = 'col-sm-6';
                
                col.innerHTML = `
                    <div class="card bg-light border-0">
                        <div class="card-body p-3">
                            <div class="d-flex align-items-center">
                                <i class="fas ${config.icon} text-primary me-3"></i>
                                <div>
                                    <div class="fw-bold">${config.label}</div>
                                    <div class="h5 mb-0 text-primary">${value} ${config.unit}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                grid.appendChild(col);
            }
        }
    }

    displayImageCharacteristics(characteristics) {
        const characteristicsSection = document.getElementById('imageCharacteristics');
        const grid = document.getElementById('characteristicsGrid');
        
        grid.innerHTML = '';

        const items = [
            { key: 'nature', icon: 'fa-eye', label: 'Nature' },
            { key: 'orientation', icon: 'fa-arrows-alt-v', label: 'Orientation' },
            { key: 'size', icon: 'fa-expand-arrows-alt', label: 'Size' },
            { key: 'magnification', icon: 'fa-search-plus', label: 'Magnification', unit: '×' }
        ];

        items.forEach(item => {
            const value = characteristics[item.key];
            if (value !== undefined) {
                const col = document.createElement('div');
                col.className = 'col-sm-6 col-md-3';
                
                col.innerHTML = `
                    <div class="text-center p-2 bg-light rounded">
                        <i class="fas ${item.icon} text-info mb-2"></i>
                        <div class="small text-muted">${item.label}</div>
                        <div class="fw-bold">${value}${item.unit || ''}</div>
                    </div>
                `;
                
                grid.appendChild(col);
            }
        });

        characteristicsSection.classList.remove('d-none');
    }

    displayRayDiagram(diagramBase64) {
        const img = document.getElementById('rayDiagram');
        img.src = `data:image/png;base64,${diagramBase64}`;
        img.style.maxWidth = '100%';
        img.style.height = 'auto';
    }

    displayErrors(errors) {
        this.hideResults();
        
        const errorAlert = document.getElementById('errorAlert');
        const errorList = document.getElementById('errorList');
        
        errorList.innerHTML = '';
        errors.forEach(error => {
            const li = document.createElement('li');
            li.textContent = error;
            errorList.appendChild(li);
        });
        
        errorAlert.classList.remove('d-none');
    }

    displayWarnings(warnings) {
        const warningAlert = document.getElementById('warningAlert');
        const warningList = document.getElementById('warningList');
        
        warningList.innerHTML = '';
        warnings.forEach(warning => {
            const li = document.createElement('li');
            li.textContent = warning;
            warningList.appendChild(li);
        });
        
        warningAlert.classList.remove('d-none');
    }

    hideErrors() {
        document.getElementById('errorAlert').classList.add('d-none');
        document.getElementById('warningAlert').classList.add('d-none');
    }

    hideResults() {
        document.getElementById('resultsCard').classList.add('d-none');
        document.getElementById('diagramCard').classList.add('d-none');
        document.getElementById('imageCharacteristics').classList.add('d-none');
    }

    showLoading(show) {
        const loadingIndicator = document.getElementById('loadingIndicator');
        if (show) {
            loadingIndicator.classList.remove('d-none');
        } else {
            loadingIndicator.classList.add('d-none');
        }
    }
}

// Initialize the calculator when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new OpticsCalculator();
});
