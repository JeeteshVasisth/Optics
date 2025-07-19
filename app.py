import os
import logging
from flask import Flask, render_template, request, jsonify
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import io
import base64
import math
import numpy as np

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_dev")

class OpticsCalculator:
    def __init__(self):
        self.reset_values()
    
    def reset_values(self):
        self.focal_length = None
        self.u = None  # object distance (negative by convention)
        self.v = None  # image distance
        self.h1 = None  # object height (positive)
        self.h2 = None  # image height
        self.errors = []
        self.warnings = []
    
    def validate_inputs(self, data, optic_type, shape):
        """Enhanced input validation with detailed error messages"""
        self.errors = []
        self.warnings = []
        
        # Check if optic type and shape are provided
        if not optic_type or not shape:
            self.errors.append("Please select both optic type and shape")
            return False
        
        # Extract and validate focal length
        if data.get('focal_length') is not None:
            try:
                f = float(data['focal_length'])
                if f == 0:
                    self.errors.append("Focal length cannot be zero")
                elif optic_type == 'mirror':
                    # For mirrors, both concave and convex typically have positive focal lengths
                    # The sign convention varies, but we'll use positive for both
                    if f <= 0:
                        self.warnings.append(f"Using absolute value of focal length for {shape} mirror")
                else:  # lens
                    if shape == 'convex' and f <= 0:
                        self.warnings.append("Convex lens focal length should be positive")
                    elif shape == 'concave' and f >= 0:
                        self.warnings.append("Concave lens focal length should be negative")
            except (ValueError, TypeError):
                self.errors.append("Focal length must be a valid number")
        
        # Validate object distance (should be negative by sign convention)
        if data.get('u') is not None:
            try:
                u = float(data['u'])
                if u >= 0:
                    self.errors.append("Object distance (u) must be negative (object is on the left side)")
            except (ValueError, TypeError):
                self.errors.append("Object distance must be a valid number")
        
        # Validate object height (should be positive)
        if data.get('h1') is not None:
            try:
                h1 = float(data['h1'])
                if h1 <= 0:
                    self.errors.append("Object height (h1) must be positive")
            except (ValueError, TypeError):
                self.errors.append("Object height must be a valid number")
        
        # Validate other numeric inputs
        for key in ['v', 'h2']:
            if data.get(key) is not None:
                try:
                    float(data[key])
                except (ValueError, TypeError):
                    self.errors.append(f"{key} must be a valid number")
        
        # Count non-None values
        given_values = sum(1 for key in ['focal_length', 'u', 'v', 'h1', 'h2'] 
                          if data.get(key) is not None)
        
        if given_values < 2:
            self.errors.append("At least 2 parameters must be provided for calculation")
        
        return len(self.errors) == 0
    
    def calculate_mirror(self, data, shape):
        """Calculate mirror parameters using proper mirror formula"""
        # Extract given values
        self.focal_length = data.get('focal_length')
        self.u = data.get('u')
        self.v = data.get('v')
        self.h1 = data.get('h1')
        self.h2 = data.get('h2')
        
        # Apply sign conventions for mirrors
        if self.focal_length is not None:
            if shape == 'concave' and self.focal_length > 0:
                self.focal_length = -abs(self.focal_length)  # Concave mirrors have negative focal length
            elif shape == 'convex' and self.focal_length < 0:
                self.focal_length = abs(self.focal_length)   # Convex mirrors have positive focal length
        
        try:
            # Mirror formula: 1/f = 1/u + 1/v
            # Note: u is negative, v can be positive or negative
            
            if self.u is not None and self.v is not None and self.focal_length is None:
                # Calculate focal length from object and image distances
                self.focal_length = (self.u * self.v) / (self.u + self.v)
                
            elif self.focal_length is not None and self.u is not None and self.v is None:
                # Calculate image distance
                # Special case: when u = f, object is at focal point, image at infinity
                if abs(self.u - self.focal_length) < 1e-6:
                    self.v = float('inf') if self.focal_length < 0 else float('-inf')
                    self.errors.append("Object at focal point - image formed at infinity (parallel rays)")
                else:
                    self.v = (self.focal_length * self.u) / (self.u - self.focal_length)
                
            elif self.focal_length is not None and self.v is not None and self.u is None:
                # Calculate object distance
                # Special case: when v = f, avoid division by zero
                if abs(self.v - self.focal_length) < 1e-6:
                    self.u = float('inf') if self.focal_length < 0 else float('-inf')
                    self.errors.append("Image at focal point - object would be at infinity")
                else:
                    self.u = (self.focal_length * self.v) / (self.v - self.focal_length)
            
            # Magnification calculations: m = -v/u = h2/h1
            if self.u is not None and self.v is not None:
                magnification = -self.v / self.u
                
                if self.h1 is not None and self.h2 is None:
                    self.h2 = magnification * self.h1
                elif self.h2 is not None and self.h1 is None:
                    self.h1 = self.h2 / magnification
            
            # If magnification info given but distances missing
            if self.h1 is not None and self.h2 is not None:
                magnification = self.h2 / self.h1
                
                if self.u is not None and self.v is None:
                    self.v = -magnification * self.u
                elif self.v is not None and self.u is None:
                    self.u = -self.v / magnification
            
            # Set default object height if not given
            if self.h1 is None and self.focal_length is not None:
                self.h1 = abs(self.focal_length) * 0.3
                if self.u is not None and self.v is not None:
                    self.h2 = -(self.v / self.u) * self.h1
            
            # Round values for display
            self._round_values()
            
            # Add image characteristics
            self._analyze_image_characteristics('mirror', shape)
            
        except (ZeroDivisionError, TypeError) as e:
            self.errors.append(f"Calculation error: {str(e)}")
            return False
        
        return True
    
    def calculate_lens(self, data, shape):
        """Calculate lens parameters using proper lens formula"""
        # Extract given values
        self.focal_length = data.get('focal_length')
        self.u = data.get('u')
        self.v = data.get('v')
        self.h1 = data.get('h1')
        self.h2 = data.get('h2')
        
        try:
            # Lens formula: 1/f = 1/v - 1/u
            # Note: u is negative, v can be positive or negative
            
            if self.u is not None and self.v is not None and self.focal_length is None:
                # Calculate focal length from object and image distances
                self.focal_length = (self.u * self.v) / (self.v - self.u)
                
            elif self.focal_length is not None and self.u is not None and self.v is None:
                # Calculate image distance
                # Special case: when u = -f, object is at focal point, image at infinity
                if abs(self.u + self.focal_length) < 1e-6:
                    self.v = float('inf') if self.focal_length > 0 else float('-inf')
                    self.errors.append("Object at focal point - image formed at infinity (parallel rays)")
                else:
                    self.v = (self.focal_length * self.u) / (self.u + self.focal_length)
                
            elif self.focal_length is not None and self.v is not None and self.u is None:
                # Calculate object distance
                # Special case: when v = f, avoid division by zero
                if abs(self.v - self.focal_length) < 1e-6:
                    self.u = float('inf') if self.focal_length > 0 else float('-inf')
                    self.errors.append("Image at focal point - object would be at infinity")
                else:
                    self.u = (self.focal_length * self.v) / (self.v - self.focal_length)
            
            # Magnification calculations: m = v/u = h2/h1
            if self.u is not None and self.v is not None:
                magnification = self.v / self.u
                
                if self.h1 is not None and self.h2 is None:
                    self.h2 = magnification * self.h1
                elif self.h2 is not None and self.h1 is None:
                    self.h1 = self.h2 / magnification
            
            # If magnification info given but distances missing
            if self.h1 is not None and self.h2 is not None:
                magnification = self.h2 / self.h1
                
                if self.u is not None and self.v is None:
                    self.v = magnification * self.u
                elif self.v is not None and self.u is None:
                    self.u = self.v / magnification
            
            # Set default object height if not given
            if self.h1 is None and self.focal_length is not None:
                self.h1 = abs(self.focal_length) * 0.3
                if self.u is not None and self.v is not None:
                    self.h2 = (self.v / self.u) * self.h1
            
            # Round values for display
            self._round_values()
            
            # Add image characteristics
            self._analyze_image_characteristics('lens', shape)
            
        except (ZeroDivisionError, TypeError) as e:
            self.errors.append(f"Calculation error: {str(e)}")
            return False
        
        return True
    
    def _round_values(self):
        """Round calculated values to reasonable precision"""
        if self.focal_length is not None and not math.isinf(self.focal_length):
            self.focal_length = round(self.focal_length, 3)
        if self.u is not None and not math.isinf(self.u):
            self.u = round(self.u, 3)
        if self.v is not None and not math.isinf(self.v):
            self.v = round(self.v, 3)
        if self.h1 is not None and not math.isinf(self.h1):
            self.h1 = round(self.h1, 3)
        if self.h2 is not None and not math.isinf(self.h2):
            self.h2 = round(self.h2, 3)
    
    def _analyze_image_characteristics(self, optic_type, shape):
        """Analyze and describe image characteristics"""
        if self.u is None or self.v is None or self.h1 is None or self.h2 is None:
            return
        
        # Handle infinite values (object at focal point)
        if math.isinf(self.v) or math.isinf(self.u):
            self.image_characteristics = {
                'nature': "Image at infinity",
                'orientation': "Parallel rays",
                'size': "Infinite",
                'magnification': "∞"
            }
            return
        
        magnification = abs(self.h2 / self.h1) if self.h1 != 0 else 0
        
        # Image nature (for mirrors: negative v means real, positive v means virtual)
        if optic_type == 'mirror':
            if self.v < 0:
                nature = "Real"
            else:
                nature = "Virtual"
        else:  # lens
            if self.v > 0:
                nature = "Real"
            else:
                nature = "Virtual"
        
        # Image orientation
        if optic_type == 'mirror':
            if self.h2 * self.h1 > 0:
                orientation = "Erect"
            else:
                orientation = "Inverted"
        else:  # lens
            if self.h2 * self.h1 > 0:
                orientation = "Erect"
            else:
                orientation = "Inverted"
        
        # Image size
        if magnification > 1:
            size = "Magnified"
        elif magnification < 1:
            size = "Diminished"
        else:
            size = "Same size"
        
        self.image_characteristics = {
            'nature': nature,
            'orientation': orientation,
            'size': size,
            'magnification': round(magnification, 3)
        }
    
    def generate_diagram(self, optic_type, shape):
        """Generate enhanced ray diagram"""
        # Skip diagram generation for focal point cases (infinite values)
        if (self.u is not None and math.isinf(self.u)) or (self.v is not None and math.isinf(self.v)):
            return self._generate_focal_point_diagram(optic_type, shape)
        
        plt.figure(figsize=(14, 10))
        plt.style.use('default')
        
        try:
            if optic_type == 'mirror':
                self._draw_mirror_diagram(shape)
            else:  # lens
                self._draw_lens_diagram(shape)
            
            plt.grid(True, alpha=0.3)
            plt.legend(loc='upper right', fontsize=10)
            plt.tight_layout()
            
            # Convert plot to base64 string
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            img_buffer.seek(0)
            img_str = base64.b64encode(img_buffer.read()).decode()
            plt.close()
            
            return img_str
        except Exception as e:
            logging.error(f"Error generating diagram: {str(e)}")
            plt.close()
            return None
    
    def _generate_focal_point_diagram(self, optic_type, shape):
        """Generate a special diagram for focal point cases showing parallel rays"""
        plt.figure(figsize=(14, 10))
        plt.style.use('default')
        
        try:
            # Use finite values for plotting
            f_val = abs(self.focal_length) if self.focal_length else 20
            axis_range = f_val * 3
            
            # Principal axis
            plt.axhline(y=0, color='black', linewidth=1, linestyle='-', alpha=0.8)
            plt.axvline(x=0, color='gray', linewidth=0.5, linestyle='--', alpha=0.5)
            
            # Draw optic surface
            if optic_type == 'mirror':
                self._draw_mirror_surface(shape, axis_range)
                # Focus point
                plt.plot(self.focal_length, 0, 'ro', markersize=8, label=f'Focus F (f={self.focal_length})')
                # Object at focus
                obj_x = self.focal_length
                obj_h = f_val * 0.3
                plt.arrow(obj_x, 0, 0, obj_h, head_width=axis_range*0.02, 
                         head_length=obj_h*0.1, fc='blue', ec='blue', linewidth=3)
                plt.text(obj_x, obj_h*1.1, 'Object at Focus', ha='center', fontsize=10, color='blue')
                
                # Draw parallel reflected rays
                for i in range(3):
                    y_start = obj_h * (0.3 + i * 0.35)
                    # Ray from object to mirror
                    plt.arrow(obj_x, y_start, -obj_x, 0, head_width=0, head_length=0, 
                             fc='red', ec='red', linewidth=2, linestyle='-')
                    # Parallel reflected ray
                    plt.arrow(0, y_start, -axis_range*0.8, 0, head_width=axis_range*0.02, 
                             head_length=axis_range*0.03, fc='red', ec='red', linewidth=2)
                
                plt.text(-axis_range*0.7, obj_h*0.7, 'Parallel Rays\n(Image at ∞)', 
                        ha='center', fontsize=12, color='red', bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
            
            plt.xlim(-axis_range, axis_range)
            plt.ylim(-axis_range*0.6, axis_range*0.6)
            plt.xlabel('Distance', fontsize=12)
            plt.ylabel('Height', fontsize=12)
            plt.title(f'{shape.title()} {optic_type.title()} - Object at Focal Point', fontsize=14, fontweight='bold')
            plt.grid(True, alpha=0.3)
            plt.legend(loc='upper right', fontsize=10)
            plt.tight_layout()
            
            # Convert to base64
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight', 
                       facecolor='white', edgecolor='none')
            img_buffer.seek(0)
            img_str = base64.b64encode(img_buffer.read()).decode()
            plt.close()
            
            return img_str
        except Exception as e:
            logging.error(f"Error generating focal point diagram: {str(e)}")
            plt.close()
            return None
    
    def _draw_mirror_diagram(self, shape):
        """Draw enhanced mirror ray diagram"""
        # Set up coordinate system with finite values only
        distances = []
        if self.u is not None and not math.isinf(self.u):
            distances.append(abs(self.u))
        if self.v is not None and not math.isinf(self.v):
            distances.append(abs(self.v))
        if self.focal_length is not None and not math.isinf(self.focal_length):
            distances.append(abs(self.focal_length))
        
        max_dist = max(distances) if distances else 10
        axis_range = max_dist * 1.3
        
        # Principal axis
        plt.axhline(y=0, color='black', linewidth=1, linestyle='-', alpha=0.8)
        plt.axvline(x=0, color='gray', linewidth=0.5, linestyle='--', alpha=0.5)
        
        # Draw mirror
        self._draw_mirror_surface(shape, axis_range)
        
        # Focus points
        if self.focal_length is not None:
            plt.plot(self.focal_length, 0, 'ro', markersize=8, label=f'Focus F (f={self.focal_length})')
            plt.plot(2*self.focal_length, 0, 'ro', markersize=6, alpha=0.7, label=f'Center C')
        
        # Object
        if self.u is not None and self.h1 is not None:
            plt.arrow(self.u, 0, 0, self.h1, head_width=axis_range*0.02, 
                     head_length=abs(self.h1)*0.1, fc='blue', ec='blue', linewidth=3)
            plt.text(self.u, self.h1*1.1, 'Object', ha='center', fontsize=10, color='blue')
        
        # Image
        if self.v is not None and self.h2 is not None:
            style = '-' if self.v > 0 else '--'
            color = 'green' if self.v > 0 else 'orange'
            plt.arrow(self.v, 0, 0, self.h2, head_width=axis_range*0.02, 
                     head_length=abs(self.h2)*0.1, fc=color, ec=color, 
                     linewidth=3, linestyle=style)
            label = 'Real Image' if self.v > 0 else 'Virtual Image'
            plt.text(self.v, self.h2*1.1, label, ha='center', fontsize=10, color=color)
        
        # Draw rays
        self._draw_mirror_rays(shape)
        
        plt.xlim(-axis_range, axis_range)
        plt.ylim(-axis_range*0.8, axis_range*0.8)
        plt.xlabel('Distance from Mirror', fontsize=12)
        plt.ylabel('Height', fontsize=12)
        plt.title(f'{shape.title()} Mirror Ray Diagram', fontsize=14, fontweight='bold')
    
    def _draw_lens_diagram(self, shape):
        """Draw enhanced lens ray diagram"""
        # Set up coordinate system with finite values only
        distances = []
        if self.u is not None and not math.isinf(self.u):
            distances.append(abs(self.u))
        if self.v is not None and not math.isinf(self.v):
            distances.append(abs(self.v))
        if self.focal_length is not None and not math.isinf(self.focal_length):
            distances.append(abs(self.focal_length))
        
        max_dist = max(distances) if distances else 10
        axis_range = max_dist * 1.3
        
        # Principal axis
        plt.axhline(y=0, color='black', linewidth=1, linestyle='-', alpha=0.8)
        plt.axvline(x=0, color='gray', linewidth=0.5, linestyle='--', alpha=0.5)
        
        # Draw lens
        self._draw_lens_surface(shape, axis_range)
        
        # Focus points
        if self.focal_length is not None:
            plt.plot([self.focal_length, -self.focal_length], [0, 0], 'ro', markersize=8)
            plt.text(self.focal_length, -axis_range*0.1, f'F ({self.focal_length})', 
                    ha='center', fontsize=10, color='red')
            plt.text(-self.focal_length, -axis_range*0.1, f'F ({-self.focal_length})', 
                    ha='center', fontsize=10, color='red')
        
        # Object
        if self.u is not None and self.h1 is not None:
            plt.arrow(self.u, 0, 0, self.h1, head_width=axis_range*0.02, 
                     head_length=abs(self.h1)*0.1, fc='blue', ec='blue', linewidth=3)
            plt.text(self.u, self.h1*1.1, 'Object', ha='center', fontsize=10, color='blue')
        
        # Image
        if self.v is not None and self.h2 is not None:
            style = '-' if self.v > 0 else '--'
            color = 'green' if self.v > 0 else 'orange'
            plt.arrow(self.v, 0, 0, self.h2, head_width=axis_range*0.02, 
                     head_length=abs(self.h2)*0.1, fc=color, ec=color, 
                     linewidth=3, linestyle=style)
            label = 'Real Image' if self.v > 0 else 'Virtual Image'
            plt.text(self.v, self.h2*1.1, label, ha='center', fontsize=10, color=color)
        
        # Draw rays
        self._draw_lens_rays(shape)
        
        plt.xlim(-axis_range, axis_range)
        plt.ylim(-axis_range*0.8, axis_range*0.8)
        plt.xlabel('Distance from Lens', fontsize=12)
        plt.ylabel('Height', fontsize=12)
        plt.title(f'{shape.title()} Lens Ray Diagram', fontsize=14, fontweight='bold')
    
    def _draw_mirror_surface(self, shape, axis_range):
        """Draw mirror surface"""
        # Make mirror height proportional to axis range but ensure minimum visibility
        mirror_height = max(axis_range * 0.6, 10)  # At least 10 units tall
        
        if shape == 'concave':
            # Concave mirror (curves inward toward the object)
            theta = np.linspace(-np.pi/3, np.pi/3, 100)
            radius = abs(self.focal_length) * 2 if self.focal_length else 20
            
            # Scale the curvature based on axis range for better visibility
            curvature_scale = max(axis_range * 0.05, 2)  # Minimum 2 units of curvature
            x = curvature_scale * np.cos(theta)  # Positive x curves toward the right (inward)
            y = mirror_height * np.sin(theta) / 2  # Scale y to mirror height
            plt.plot(x, y, 'red', linewidth=4, label='Concave Mirror')
        else:
            # Convex mirror (curves outward away from the object)
            theta = np.linspace(-np.pi/3, np.pi/3, 100)
            radius = abs(self.focal_length) * 2 if self.focal_length else 20
            
            # Scale the curvature based on axis range for better visibility
            curvature_scale = max(axis_range * 0.05, 2)  # Minimum 2 units of curvature
            x = -curvature_scale * np.cos(theta)  # Negative x curves toward the left (outward)
            y = mirror_height * np.sin(theta) / 2  # Scale y to mirror height
            plt.plot(x, y, 'red', linewidth=4, label='Convex Mirror')
    
    def _draw_lens_surface(self, shape, axis_range):
        """Draw lens surface"""
        lens_height = axis_range * 0.6
        
        if shape == 'convex':
            # Convex lens (biconvex)
            y_vals = np.linspace(-lens_height, lens_height, 100)
            thickness = lens_height * 0.1
            x_left = -thickness * (1 - (y_vals / lens_height) ** 2)
            x_right = thickness * (1 - (y_vals / lens_height) ** 2)
            plt.plot(x_left, y_vals, 'red', linewidth=3)
            plt.plot(x_right, y_vals, 'red', linewidth=3, label='Convex Lens')
        else:
            # Concave lens (biconcave)
            y_vals = np.linspace(-lens_height, lens_height, 100)
            thickness = lens_height * 0.1
            x_left = thickness * (1 - (y_vals / lens_height) ** 2)
            x_right = -thickness * (1 - (y_vals / lens_height) ** 2)
            plt.plot(x_left, y_vals, 'red', linewidth=3)
            plt.plot(x_right, y_vals, 'red', linewidth=3, label='Concave Lens')
    
    def _draw_mirror_rays(self, shape):
        """Draw principal rays for mirrors"""
        if not all([self.u, self.v, self.h1, self.h2, self.focal_length]):
            return
        
        # Skip ray drawing for infinite values
        if (math.isinf(self.u) or math.isinf(self.v) or 
            math.isinf(self.h1) or math.isinf(self.h2) or 
            math.isinf(self.focal_length)):
            return
        
        try:
            # Ensure all values are numeric
            u_val = float(self.u)
            v_val = float(self.v)
            h1_val = float(self.h1)
            h2_val = float(self.h2)
            f_val = float(self.focal_length)
            
            # Calculate mirror surface position for ray intersection
            # Use the same scaling as in _draw_mirror_surface
            distances = []
            if self.u is not None and not math.isinf(self.u):
                distances.append(abs(self.u))
            if self.v is not None and not math.isinf(self.v):
                distances.append(abs(self.v))
            if self.focal_length is not None and not math.isinf(self.focal_length):
                distances.append(abs(self.focal_length))
            
            max_dist = max(distances) if distances else 10
            axis_range = max_dist * 1.3
            curvature_scale = max(axis_range * 0.05, 2)  # Same as in mirror surface drawing
            
            mirror_x = curvature_scale if shape == 'concave' else -curvature_scale
            
            # Determine if rays should be dotted (for virtual AND erect images)
            # For mirrors: Virtual images have v > 0, erect images have same sign for h1 and h2
            is_virtual = v_val > 0  # For mirrors: positive v means virtual
            is_erect = (h1_val * h2_val) > 0  # Same sign means erect
            ray_style = '--' if (is_virtual and is_erect) else '-'  # Dotted only for virtual AND erect
            
            # Ray 1: Parallel to axis, reflects through focus
            plt.plot([u_val, mirror_x], [h1_val, h1_val], 'blue', linewidth=2, alpha=0.8, label='Ray 1: Parallel to axis')
            plt.plot([mirror_x, v_val], [h1_val, h2_val], 'blue', linewidth=2, alpha=0.8, linestyle=ray_style)
            
            # Ray 2: Through focus to mirror, reflects parallel to axis
            if shape == 'concave':
                # Ray from object tip through focus to mirror
                # Calculate where the ray through focus intersects the mirror surface
                # The ray goes from (u_val, h1_val) through (f_val, 0) and hits the mirror
                
                # Calculate the slope and find intersection with mirror
                if f_val != u_val:  # Avoid division by zero
                    slope = (0 - h1_val) / (f_val - u_val)
                    # Find y-coordinate where ray hits mirror at x = mirror_x
                    mirror_y_intersect = h1_val + slope * (mirror_x - u_val)
                    
                    # Draw ray from object through focus to mirror
                    plt.plot([u_val, mirror_x], [h1_val, mirror_y_intersect], 'red', linewidth=2, alpha=0.8, label='Ray 2: Through focus')
                    # Reflected ray goes parallel to axis (same height as intersection point)
                    plt.plot([mirror_x, v_val], [mirror_y_intersect, mirror_y_intersect], 'red', linewidth=2, alpha=0.8, linestyle=ray_style)
            else:
                # For convex mirror: ray aimed toward focus (behind mirror) reflects parallel
                plt.plot([u_val, mirror_x], [h1_val, h1_val], 'red', linewidth=2, alpha=0.8, label='Ray 2: Toward focus')
                plt.plot([mirror_x, v_val], [h1_val, h2_val], 'red', linewidth=2, alpha=0.8, linestyle=ray_style)
            
            # Ray 3: Through center of curvature (normal incidence)
            center = 2 * f_val
            plt.plot([u_val, mirror_x], [h1_val, h1_val], 'green', linewidth=2, alpha=0.6, label='Ray 3: Normal incidence')
            plt.plot([mirror_x, v_val], [h1_val, h2_val], 'green', linewidth=2, alpha=0.6, linestyle=ray_style)
            
        except (ValueError, TypeError):
            pass  # Skip ray drawing if values are invalid
    
    def _draw_lens_rays(self, shape):
        """Draw principal rays for lenses"""
        if not all([self.u, self.v, self.h1, self.h2, self.focal_length]):
            return
        
        # Skip ray drawing for infinite values
        if (math.isinf(self.u) or math.isinf(self.v) or 
            math.isinf(self.h1) or math.isinf(self.h2) or 
            math.isinf(self.focal_length)):
            return
        
        try:
            # Ensure all values are numeric
            u_val = float(self.u)
            v_val = float(self.v)
            h1_val = float(self.h1)
            h2_val = float(self.h2)
            f_val = float(self.focal_length)
            
            # Ray 1: Parallel to axis, refracts through focus
            plt.plot([u_val, 0], [h1_val, h1_val], 'gray', linewidth=1.5, alpha=0.8, label='Incident Ray')
            plt.plot([0, v_val], [h1_val, h2_val], 'gray', linewidth=1.5, alpha=0.8, label='Refracted Ray')
            
            # Ray 2: Through optical center (undeviated)
            plt.plot([u_val, v_val], [h1_val, h2_val], 'lightblue', linewidth=1.5, alpha=0.8, label='Central Ray')
            
            # Ray 3: Through focus, emerges parallel to axis (for convex lens)
            if shape == 'convex' and f_val > 0:
                plt.plot([u_val, -f_val], [h1_val, 0], 'lightgreen', linewidth=1, alpha=0.6)
                plt.plot([-f_val, 0], [0, h1_val], 'lightgreen', linewidth=1, alpha=0.6)
                plt.plot([0, v_val], [h1_val, h2_val], 'lightgreen', linewidth=1, alpha=0.6)
        except (ValueError, TypeError):
            pass  # Skip ray drawing if values are invalid

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        data = request.get_json()
        optic_type = data.get('optic_type')
        shape = data.get('shape')
        
        # Extract numerical inputs
        inputs = {}
        for key in ['focal_length', 'u', 'v', 'h1', 'h2']:
            value = data.get(key)
            if value is not None and str(value).strip() != '':
                try:
                    inputs[key] = float(value)
                except ValueError:
                    return jsonify({
                        'success': False,
                        'errors': [f"Invalid value for {key}: must be a number"]
                    })
        
        calculator = OpticsCalculator()
        
        # Validate inputs
        if not calculator.validate_inputs(inputs, optic_type, shape):
            return jsonify({
                'success': False,
                'errors': calculator.errors
            })
        
        # Perform calculations
        if optic_type == 'mirror':
            success = calculator.calculate_mirror(inputs, shape)
        else:
            success = calculator.calculate_lens(inputs, shape)
        
        if not success:
            return jsonify({
                'success': False,
                'errors': calculator.errors
            })
        
        # Generate diagram
        diagram_base64 = calculator.generate_diagram(optic_type, shape)
        
        # Convert infinite values to strings for JSON response
        def safe_value(val):
            if val is None:
                return None
            elif math.isinf(val):
                return "∞" if val > 0 else "-∞"
            else:
                return val
        
        # Prepare response
        result = {
            'success': True,
            'results': {
                'focal_length': safe_value(calculator.focal_length),
                'u': safe_value(calculator.u),
                'v': safe_value(calculator.v),
                'h1': safe_value(calculator.h1),
                'h2': safe_value(calculator.h2)
            },
            'diagram': diagram_base64,
            'warnings': calculator.warnings
        }
        
        # Add image characteristics if available
        if hasattr(calculator, 'image_characteristics'):
            result['image_characteristics'] = calculator.image_characteristics
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Calculation error: {str(e)}")
        return jsonify({
            'success': False,
            'errors': [f"Server error: {str(e)}"]
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
