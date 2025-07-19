from flask import Flask, render_template, request, jsonify, send_file
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import io
import base64
import json
import math

app = Flask(__name__)

class OpticsCalculator:
    def __init__(self):
        self.reset_values()
    
    def reset_values(self):
        self.focal_length = None
        self.u = None
        self.v = None
        self.h1 = None
        self.h2 = None
        self.errors = []
    
    def validate_inputs(self, data, optic_type, shape):
        """Validate input values based on optic type and shape"""
        self.errors = []
        
        # Validate focal length
        if data.get('focal_length') is not None:
            f = data['focal_length']
            if shape == 'concave' and f >= 0:
                self.errors.append("Concave focal length must be negative")
            elif shape == 'convex' and optic_type == 'mirror' and f <= 0:
                self.errors.append("Convex mirror focal length must be positive")
            elif shape == 'convex' and optic_type == 'lens' and f <= 0:
                self.errors.append("Convex lens focal length must be positive")
        
        # Validate object distance (always negative)
        if data.get('u') is not None and data['u'] >= 0:
            self.errors.append("Object distance (u) must be negative")
        
        # Validate image distance for specific cases
        if optic_type == 'mirror' and shape == 'convex':
            if data.get('v') is not None and data['v'] <= 0:
                self.errors.append("Image distance (v) for convex mirror must be positive")
        elif optic_type == 'lens' and shape == 'concave':
            if data.get('v') is not None and data['v'] >= 0:
                self.errors.append("Image distance (v) for concave lens must be negative")
        
        # Validate heights
        if data.get('h1') is not None and data['h1'] <= 0:
            self.errors.append("Object height (h1) must be positive")
        
        if optic_type == 'mirror' and shape == 'convex':
            if data.get('h2') is not None and data['h2'] <= 0:
                self.errors.append("Image height (h2) for convex mirror must be positive")
        elif optic_type == 'lens' and shape == 'concave':
            if data.get('h2') is not None and data['h2'] <= 0:
                self.errors.append("Image height (h2) for concave lens must be positive")
        
        return len(self.errors) == 0
    
    def calculate_mirror(self, data, shape):
        """Calculate mirror parameters"""
        # Extract given values
        self.focal_length = data.get('focal_length')
        self.u = data.get('u')
        self.v = data.get('v')
        self.h1 = data.get('h1')
        self.h2 = data.get('h2')
        
        try:
            # Calculate missing values using mirror formula: 1/f = 1/v + 1/u
            if self.u is not None and self.v is not None and self.focal_length is None:
                self.focal_length = 1 / (1/self.v + 1/self.u)
            elif self.focal_length is not None and self.v is not None and self.u is None:
                self.u = 1 / (1/self.focal_length - 1/self.v)
            elif self.u is not None and self.focal_length is not None and self.v is None:
                self.v = 1 / (1/self.focal_length - 1/self.u)
            
            # Calculate using magnification: m = -v/u = h2/h1
            if self.u is not None and self.h1 is not None and self.h2 is not None and self.v is None:
                self.v = (-self.h2 * self.u) / self.h1
            elif self.v is not None and self.h1 is not None and self.h2 is not None and self.u is None:
                self.u = (-self.v * self.h1) / self.h2
            elif self.h1 is not None and self.h2 is None and self.u is not None and self.v is not None:
                self.h2 = (-self.u * self.h1) / self.v
            elif self.h2 is not None and self.h1 is None and self.u is not None and self.v is not None:
                if shape == 'concave':
                    self.h1 = (-self.v * self.h2) / self.u
                else:  # convex
                    self.h1 = (-self.v * self.h2) / self.u
            
            # If heights not given, assume reasonable values for diagram
            if self.h1 is None and self.h2 is None and self.focal_length is not None:
                if shape == 'concave':
                    self.h1 = -self.focal_length / 4
                else:
                    self.h1 = self.focal_length / 4
                if self.u is not None and self.v is not None:
                    self.h2 = (-self.h1 * self.v) / self.u
            
            # Round values
            if self.focal_length is not None:
                self.focal_length = round(self.focal_length, 2)
            if self.u is not None:
                self.u = round(self.u, 2)
            if self.v is not None:
                self.v = round(self.v, 2)
            if self.h1 is not None:
                self.h1 = round(self.h1, 2)
            if self.h2 is not None:
                self.h2 = round(self.h2, 2)
            
        except (ZeroDivisionError, TypeError):
            self.errors.append("Invalid calculation - check your input values")
            return False
        
        return True
    
    def calculate_lens(self, data, shape):
        """Calculate lens parameters"""
        # Extract given values
        self.focal_length = data.get('focal_length')
        self.u = data.get('u')
        self.v = data.get('v')
        self.h1 = data.get('h1')
        self.h2 = data.get('h2')
        
        try:
            # Calculate missing values using lens formula: 1/f = 1/v - 1/u
            if self.u is not None and self.v is not None and self.focal_length is None:
                self.focal_length = 1 / (1/self.v - 1/self.u)
            elif self.focal_length is not None and self.v is not None and self.u is None:
                self.u = 1 / (-1/self.focal_length + 1/self.v)
            elif self.u is not None and self.focal_length is not None and self.v is None:
                self.v = 1 / (1/self.focal_length + 1/self.u)
            
            # Calculate using magnification: m = v/u = h2/h1
            if self.u is not None and self.h1 is not None and self.h2 is not None and self.v is None:
                self.v = (self.h2 * self.u) / self.h1
            elif self.v is not None and self.h1 is not None and self.h2 is not None and self.u is None:
                self.u = (self.v * self.h1) / self.h2
            elif self.h1 is not None and self.h2 is None and self.u is not None and self.v is not None:
                if shape == 'convex':
                    self.h2 = (self.v * self.h1) / self.u
                else:  # concave
                    self.h2 = (self.u * self.h1) / self.v
            elif self.h2 is not None and self.h1 is None and self.u is not None and self.v is not None:
                if shape == 'convex':
                    self.h1 = (self.u * self.h2) / self.v
                else:  # concave
                    self.h1 = (self.v * self.h2) / self.u
            
            # If heights not given, assume reasonable values for diagram
            if self.h1 is None and self.h2 is None and self.focal_length is not None:
                if shape == 'concave':
                    self.h1 = -self.focal_length / 4
                else:
                    self.h1 = self.focal_length / 4
                if self.u is not None and self.v is not None:
                    if shape == 'convex':
                        self.h2 = (self.h1 * self.v) / self.u
                    else:
                        self.h2 = (self.h1 * self.v) / self.u
            
            # Round values
            if self.focal_length is not None:
                self.focal_length = round(self.focal_length, 2)
            if self.u is not None:
                self.u = round(self.u, 2)
            if self.v is not None:
                self.v = round(self.v, 2)
            if self.h1 is not None:
                self.h1 = round(self.h1, 2)
            if self.h2 is not None:
                self.h2 = round(self.h2, 2)
            
        except (ZeroDivisionError, TypeError):
            self.errors.append("Invalid calculation - check your input values")
            return False
        
        return True
    
    def generate_diagram(self, optic_type, shape):
        """Generate ray diagram"""
        plt.figure(figsize=(12, 8))
        plt.axis('equal')
        plt.grid(True, alpha=0.3)
        
        try:
            if optic_type == 'mirror':
                self._draw_mirror_diagram(shape)
            else:  # lens
                self._draw_lens_diagram(shape)
            
            # Convert plot to base64 string
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
            img_buffer.seek(0)
            img_str = base64.b64encode(img_buffer.read()).decode()
            plt.close()
            
            return img_str
        except Exception as e:
            plt.close()
            return None
    
    def _draw_mirror_diagram(self, shape):
        """Draw mirror ray diagram"""
        # Object and image
        if self.u is not None and self.h1 is not None:
            plt.plot([self.u, self.u], [0, self.h1], 'b-', linewidth=3, label='Object')
        
        if self.v is not None and self.h2 is not None:
            plt.plot([self.v, self.v], [0, self.h2], 'g--', linewidth=3, label='Image')
        
        # Draw mirror curve
        if self.focal_length is not None:
            mirror_radius = abs(self.focal_length)
            num_points = 100
            y_values = []
            x_values = []
            
            y = -mirror_radius
            step = (2 * mirror_radius) / num_points
            
            for _ in range(num_points):
                if shape == 'concave':
                    x = (1 / (4 * abs(self.focal_length))) * y ** 2
                    y_values.append(-y)
                else:  # convex
                    x = -(1 / (4 * abs(self.focal_length))) * y ** 2
                    y_values.append(y)
                x_values.append(x)
                y += step
            
            plt.plot(x_values, y_values, 'r-', linewidth=2, label=f'{shape.title()} Mirror')
        
        # Draw rays
        if all(val is not None for val in [self.u, self.v, self.h1, self.h2]):
            # Ray 1: parallel to axis, reflects through focus
            ray1_x = [self.u, 0, self.v]
            ray1_y = [self.h1, self.h1, self.h2]
            plt.plot(ray1_x, ray1_y, 'gray', linewidth=1, alpha=0.7)
            
            # Ray 2: through center
            ray2_x = [self.u, 0, self.v]
            ray2_y = [self.h1, 0, self.h2]
            plt.plot(ray2_x, ray2_y, 'gray', linewidth=1, alpha=0.7)
        
        # Principal axis
        axis_range = max(abs(self.u) if self.u else 10, abs(self.v) if self.v else 10) + 5
        plt.plot([-axis_range, axis_range], [0, 0], 'k-', linewidth=1, label='Principal Axis')
        
        # Focus point
        if self.focal_length is not None:
            plt.plot(self.focal_length, 0, 'ro', markersize=8, label=f'Focus (f={self.focal_length})')
        
        plt.legend()
        plt.title(f'{shape.title()} Mirror Ray Diagram')
        plt.xlabel('Distance')
        plt.ylabel('Height')
    
    def _draw_lens_diagram(self, shape):
        """Draw lens ray diagram"""
        # Object and image
        if self.u is not None and self.h1 is not None:
            plt.plot([self.u, self.u], [0, self.h1], 'b-', linewidth=3, label='Object')
        
        if self.v is not None and self.h2 is not None:
            plt.plot([self.v, self.v], [0, self.h2], 'g--', linewidth=3, label='Image')
        
        # Draw lens
        if self.focal_length is not None:
            lens_height = abs(self.focal_length)
            
            if shape == 'convex':
                # Convex lens (biconvex)
                y_vals = []
                x_vals_left = []
                x_vals_right = []
                
                y = -lens_height
                step = (2 * lens_height) / 100
                
                for _ in range(100):
                    curve_x = (1 / (8 * abs(self.focal_length))) * y ** 2
                    x_vals_left.append(-curve_x)
                    x_vals_right.append(curve_x)
                    y_vals.append(y)
                    y += step
                
                plt.plot(x_vals_left, y_vals, 'r-', linewidth=2)
                plt.plot(x_vals_right, y_vals, 'r-', linewidth=2, label='Convex Lens')
                
            else:  # concave
                # Concave lens (biconcave)
                lens_thickness = abs(self.focal_length) / 10
                y_vals = []
                x_vals_left = []
                x_vals_right = []
                
                y = -lens_height
                step = (2 * lens_height) / 100
                
                for _ in range(100):
                    curve_x = (1 / (8 * abs(self.focal_length))) * y ** 2
                    x_vals_left.append(curve_x - lens_thickness)
                    x_vals_right.append(-curve_x + lens_thickness)
                    y_vals.append(y)
                    y += step
                
                plt.plot(x_vals_left, y_vals, 'r-', linewidth=2)
                plt.plot(x_vals_right, y_vals, 'r-', linewidth=2, label='Concave Lens')
                
                # Connect top and bottom
                plt.plot([x_vals_left[0], x_vals_right[0]], [y_vals[0], y_vals[0]], 'r-', linewidth=2)
                plt.plot([x_vals_left[-1], x_vals_right[-1]], [y_vals[-1], y_vals[-1]], 'r-', linewidth=2)
        
        # Draw rays
        if all(val is not None for val in [self.u, self.v, self.h1, self.h2]):
            # Ray 1: parallel to axis
            ray1_x = [self.u, 0, self.v]
            ray1_y = [self.h1, self.h1, self.h2]
            plt.plot(ray1_x, ray1_y, 'gray', linewidth=1, alpha=0.7)
            
            # Ray 2: through optical center
            ray2_x = [self.u, 0, self.v]
            ray2_y = [self.h1, 0, self.h2]
            plt.plot(ray2_x, ray2_y, 'gray', linewidth=1, alpha=0.7)
        
        # Principal axis
        axis_range = max(abs(self.u) if self.u else 10, abs(self.v) if self.v else 10) + 5
        plt.plot([-axis_range, axis_range], [0, 0], 'k-', linewidth=1, label='Principal Axis')
        
        # Focus points
        if self.focal_length is not None:
            plt.plot(self.focal_length, 0, 'ro', markersize=6, label=f'F1 (f={self.focal_length})')
            plt.plot(-self.focal_length, 0, 'ro', markersize=6, label=f'F2 (f={-self.focal_length})')
        
        plt.legend()
        plt.title(f'{shape.title()} Lens Ray Diagram')
        plt.xlabel('Distance')
        plt.ylabel('Height')

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Optics Calculator</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
            }
            
            .container {
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            
            h1 {
                color: #2c3e50;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
            }
            
            .form-section {
                margin-bottom: 25px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                border-left: 4px solid #3498db;
            }
            
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #2c3e50;
            }
            
            select, input {
                width: 100%;
                padding: 12px;
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                font-size: 16px;
                transition: border-color 0.3s ease;
            }
            
            select:focus, input:focus {
                outline: none;
                border-color: #3498db;
                box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
            }
            
            .input-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }
            
            button {
                background: linear-gradient(135deg, #3498db, #2980b9);
                color: white;
                padding: 15px 30px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 18px;
                font-weight: 600;
                width: 100%;
                margin-top: 20px;
                transition: all 0.3s ease;
            }
            
            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(52, 152, 219, 0.3);
            }
            
            .results {
                background: #e8f5e8;
                padding: 20px;
                border-radius: 10px;
                border-left: 4px solid #27ae60;
                margin-top: 20px;
            }
            
            .error {
                background: #ffe6e6;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #e74c3c;
                margin-top: 15px;
                color: #c0392b;
            }
            
            .diagram-container {
                text-align: center;
                margin-top: 30px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
            }
            
            .diagram-container img {
                max-width: 100%;
                height: auto;
                border-radius: 8px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            
            .help-text {
                font-size: 0.9em;
                color: #7f8c8d;
                font-style: italic;
                margin-top: 5px;
            }
            
            @media (max-width: 768px) {
                .input-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔬 Advanced Optics Calculator</h1>
            
            <form id="opticsForm">
                <div class="form-section">
                    <label for="optic_type">Select Optical Element:</label>
                    <select id="optic_type" name="optic_type" required>
                        <option value="">Choose...</option>
                        <option value="mirror">Mirror</option>
                        <option value="lens">Lens</option>
                    </select>
                </div>
                
                <div class="form-section">
                    <label for="shape">Select Shape:</label>
                    <select id="shape" name="shape" required>
                        <option value="">Choose...</option>
                        <option value="concave">Concave</option>
                        <option value="convex">Convex</option>
                    </select>
                </div>
                
                <div class="form-section">
                    <label>Enter Known Values:</label>
                    <p class="help-text">Leave blank for unknown values. Enter negative values where appropriate.</p>
                    
                    <div class="input-grid">
                        <div>
                            <label for="focal_length">Focal Length (f):</label>
                            <input type="number" id="focal_length" name="focal_length" step="0.01" placeholder="Enter focal length">
                            <div class="help-text">Negative for concave, positive for convex</div>
                        </div>
                        
                        <div>
                            <label for="u">Object Distance (u):</label>
                            <input type="number" id="u" name="u" step="0.01" placeholder="Enter object distance">
                            <div class="help-text">Always negative (object on left)</div>
                        </div>
                        
                        <div>
                            <label for="v">Image Distance (v):</label>
                            <input type="number" id="v" name="v" step="0.01" placeholder="Enter image distance">
                            <div class="help-text">Sign indicates image position</div>
                        </div>
                        
                        <div>
                            <label for="h1">Object Height (h₁):</label>
                            <input type="number" id="h1" name="h1" step="0.01" placeholder="Enter object height">
                            <div class="help-text">Always positive</div>
                        </div>
                        
                        <div>
                            <label for="h2">Image Height (h₂):</label>
                            <input type="number" id="h2" name="h2" step="0.01" placeholder="Enter image height">
                            <div class="help-text">Sign indicates image orientation</div>
                        </div>
                    </div>
                </div>
                
                <button type="submit">🔍 Calculate & Generate Diagram</button>
            </form>
        </div>
        
        <div id="results"></div>
        
        <script>
            document.getElementById('opticsForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                const data = Object.fromEntries(formData);
                
                // Convert numeric fields
                ['focal_length', 'u', 'v', 'h1', 'h2'].forEach(field => {
                    if (data[field] && data[field].trim() !== '') {
                        data[field] = parseFloat(data[field]);
                    } else {
                        delete data[field];
                    }
                });
                
                try {
                    const response = await fetch('/calculate', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    displayResults(result);
                } catch (error) {
                    console.error('Error:', error);
                    document.getElementById('results').innerHTML = '<div class="error">An error occurred while calculating. Please try again.</div>';
                }
            });
            
            function displayResults(result) {
                const resultsDiv = document.getElementById('results');
                
                if (!result.success) {
                    resultsDiv.innerHTML = `
                        <div class="container">
                            <div class="error">
                                <h3>❌ Calculation Error</h3>
                                <ul>
                                    ${result.errors.map(error => `<li>${error}</li>`).join('')}
                                </ul>
                            </div>
                        </div>
                    `;
                    return;
                }
                
                let resultsHTML = `
                    <div class="container">
                        <div class="results">
                            <h3>✅ Calculated Results</h3>
                            <div class="input-grid">
                `;
                
                if (result.focal_length !== null) {
                    resultsHTML += `<div><strong>Focal Length (f):</strong> ${result.focal_length}</div>`;
                }
                if (result.u !== null) {
                    resultsHTML += `<div><strong>Object Distance (u):</strong> ${result.u}</div>`;
                }
                if (result.v !== null) {
                    resultsHTML += `<div><strong>Image Distance (v):</strong> ${result.v}</div>`;
                }
                if (result.h1 !== null) {
                    resultsHTML += `<div><strong>Object Height (h₁):</strong> ${result.h1}</div>`;
                }
                if (result.h2 !== null) {
                    resultsHTML += `<div><strong>Image Height (h₂):</strong> ${result.h2}</div>`;
                }
                
                resultsHTML += `
                            </div>
                        </div>
                `;
                
                if (result.diagram) {
                    resultsHTML += `
                        <div class="diagram-container">
                            <h3>📊 Ray Diagram</h3>
                            <img src="data:image/png;base64,${result.diagram}" alt="Ray Diagram">
                        </div>
                    `;
                }
                
                resultsHTML += `</div>`;
                resultsDiv.innerHTML = resultsHTML;
            }
        </script>
    </body>
    </html>
    '''

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        optic_type = data.get('optic_type')
        shape = data.get('shape')
        
        if not optic_type or not shape:
            return jsonify({
                'success': False,
                'errors': ['Please select both optic type and shape']
            })
        
        calculator = OpticsCalculator()
        
        # Validate inputs
        if not calculator.validate_inputs(data, optic_type, shape):
            return jsonify({
                'success': False,
                'errors': calculator.errors
            })
        
        # Calculate based on type
        if optic_type == 'mirror':
            success = calculator.calculate_mirror(data, shape)
        else:  # lens
            success = calculator.calculate_lens(data, shape)
        
        if not success:
            return jsonify({
                'success': False,
                'errors': calculator.errors
            })
        
        # Generate diagram
        diagram_base64 = calculator.generate_diagram(optic_type, shape)
        
        return jsonify({
            'success': True,
            'focal_length': calculator.focal_length,
            'u': calculator.u,
            'v': calculator.v,
            'h1': calculator.h1,
            'h2': calculator.h2,
            'diagram': diagram_base64
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'errors': [f'An unexpected error occurred: {str(e)}']
        })

if __name__ == '__main__':
    app.run(debug=True)
