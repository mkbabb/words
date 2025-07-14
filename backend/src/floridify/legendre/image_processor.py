"""Image to complex array conversion with optimal path extraction."""

from __future__ import annotations
import numpy as np
from numpy.typing import NDArray
import cv2
import vtracer
from io import BytesIO
from PIL import Image
from scipy.spatial import distance_matrix
from scipy.signal import hilbert


class ImageToPathConverter:
    """Multi-phase image to single continuous path conversion."""
    
    def __init__(self, n_points: int = 1000):
        self.n_points = n_points
    
    def image_to_feature_points(self, image_data: bytes, 
                               method: str = "edge") -> NDArray[np.float64]:
        """Extract feature points from image using specified method."""
        # Load image
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        if method == "edge":
            points = self._edge_based_extraction(img)
        elif method == "contour":
            points = self._contour_based_extraction(img)
        elif method == "vector":
            points = self._vector_based_extraction(image_data)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Subsample if too many points
        if len(points) > self.n_points:
            indices = np.linspace(0, len(points)-1, self.n_points, dtype=int)
            points = points[indices]
        
        return points
    
    def _edge_based_extraction(self, img: NDArray[np.uint8]) -> NDArray[np.float64]:
        """Extract points along edges using Canny detector."""
        # Preprocessing
        blurred = cv2.GaussianBlur(img, (5, 5), 1.0)
        
        # Multi-scale edge detection
        edges1 = cv2.Canny(blurred, 50, 150)
        edges2 = cv2.Canny(blurred, 100, 200)
        edges = cv2.bitwise_or(edges1, edges2)
        
        # Get edge points
        y_coords, x_coords = np.where(edges > 0)
        if len(x_coords) == 0:
            # Fallback to threshold
            _, binary = cv2.threshold(blurred, 128, 255, cv2.THRESH_BINARY)
            y_coords, x_coords = np.where(binary > 0)
        
        points = np.column_stack((x_coords, y_coords))
        return points.astype(np.float64)
    
    def _contour_based_extraction(self, img: NDArray[np.uint8]) -> NDArray[np.float64]:
        """Extract points from contours."""
        # Adaptive thresholding for better contour detection
        binary = cv2.adaptiveThreshold(
            img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Find contours
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Combine all contour points
        all_points = []
        for contour in contours:
            # Approximate contour to reduce points
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            all_points.extend(approx.squeeze())
        
        if not all_points:
            # Fallback to edge detection
            return self._edge_based_extraction(img)
        
        return np.array(all_points, dtype=np.float64)
    
    def _vector_based_extraction(self, image_data: bytes) -> NDArray[np.float64]:
        """Use VTracer for high-quality vectorization."""
        # Convert using VTracer
        svg_str = vtracer.convert_raw_image_to_svg(
            image_data,
            colormode='binary',
            hierarchical='stacked',
            mode='polygon',
            filter_speckle=4,
            color_precision=6,
            layer_difference=16,
            corner_threshold=60,
            length_threshold=4.0,
            splice_threshold=45,
            max_iterations=10
        )
        
        # Parse SVG paths to extract points
        points = self._parse_svg_paths(svg_str)
        return points
    
    def _parse_svg_paths(self, svg_str: str) -> NDArray[np.float64]:
        """Extract points from SVG path data."""
        import re
        
        points = []
        # Simple regex to extract coordinates from path commands
        path_pattern = r'[ML]\s*([\d.]+)\s+([\d.]+)'
        matches = re.findall(path_pattern, svg_str)
        
        for x, y in matches:
            points.append([float(x), float(y)])
        
        if not points:
            # Fallback: create a grid
            x = np.linspace(0, 100, 20)
            y = np.linspace(0, 100, 20)
            xx, yy = np.meshgrid(x, y)
            points = np.column_stack((xx.ravel(), yy.ravel()))
        
        return np.array(points, dtype=np.float64)
    
    def find_optimal_path(self, points: NDArray[np.float64], 
                         method: str = "nearest") -> NDArray[np.int32]:
        """Find optimal tour through points."""
        n = len(points)
        if n <= 2:
            return np.arange(n)
        
        if method == "nearest":
            return self._nearest_neighbor_tsp(points)
        elif method == "christofides":
            return self._christofides_approximation(points)
        else:
            raise ValueError(f"Unknown TSP method: {method}")
    
    def _nearest_neighbor_tsp(self, points: NDArray[np.float64]) -> NDArray[np.int32]:
        """Greedy nearest neighbor TSP approximation."""
        n = len(points)
        unvisited = set(range(1, n))
        path = [0]  # Start at first point
        current = 0
        
        # Build distance matrix
        dists = distance_matrix(points, points)
        
        while unvisited:
            # Find nearest unvisited point
            nearest_dist = np.inf
            nearest_idx = -1
            for idx in unvisited:
                if dists[current, idx] < nearest_dist:
                    nearest_dist = dists[current, idx]
                    nearest_idx = idx
            
            path.append(nearest_idx)
            unvisited.remove(nearest_idx)
            current = nearest_idx
        
        return np.array(path)
    
    def _christofides_approximation(self, points: NDArray[np.float64]) -> NDArray[np.int32]:
        """Simplified Christofides-like approximation."""
        # For true Christofides, we'd need MST + perfect matching
        # This is a simplified version using nearest neighbor with 2-opt
        path = self._nearest_neighbor_tsp(points)
        
        # Apply 2-opt improvement
        improved = True
        dists = distance_matrix(points, points)
        
        while improved:
            improved = False
            for i in range(1, len(path) - 2):
                for j in range(i + 1, len(path)):
                    if j - i == 1:
                        continue
                    
                    # Check if reversing path[i:j] improves tour
                    curr_dist = (dists[path[i-1], path[i]] + 
                               dists[path[j-1], path[j % len(path)]])
                    new_dist = (dists[path[i-1], path[j-1]] + 
                              dists[path[i], path[j % len(path)]])
                    
                    if new_dist < curr_dist:
                        path[i:j] = path[i:j][::-1]
                        improved = True
                        break
                if improved:
                    break
        
        return path
    
    def points_to_complex_array(self, points: NDArray[np.float64], 
                               path_indices: NDArray[np.int32]) -> NDArray[np.complex128]:
        """Convert ordered points to normalized complex array."""
        # Order points according to path
        ordered_points = points[path_indices]
        
        # Normalize to [-1, 1]
        x_min, y_min = ordered_points.min(axis=0)
        x_max, y_max = ordered_points.max(axis=0)
        
        x_norm = 2 * (ordered_points[:, 0] - x_min) / (x_max - x_min + 1e-10) - 1
        y_norm = 2 * (ordered_points[:, 1] - y_min) / (y_max - y_min + 1e-10) - 1
        
        # Combine as complex numbers
        return x_norm + 1j * y_norm


class ImageComplexEncoder:
    """High-level interface for image to complex array encoding."""
    
    def __init__(self, n_points: int = 1000):
        self.converter = ImageToPathConverter(n_points)
    
    def encode(self, image_data: bytes, method: str = "auto") -> NDArray[np.complex128]:
        """Convert image to complex array using optimal path."""
        if method == "auto":
            # Try vector first, fallback to edge
            try:
                points = self.converter.image_to_feature_points(image_data, "vector")
            except:
                points = self.converter.image_to_feature_points(image_data, "edge")
        else:
            points = self.converter.image_to_feature_points(image_data, method)
        
        # Find optimal path
        path = self.converter.find_optimal_path(points, "nearest")
        
        # Convert to complex array
        return self.converter.points_to_complex_array(points, path)
    
    def encode_with_hilbert(self, image_data: bytes) -> NDArray[np.complex128]:
        """Encode using grayscale + Hilbert transform."""
        # Load as grayscale
        img = Image.open(BytesIO(image_data)).convert('L')
        gray = np.array(img).flatten()
        
        # Normalize to [-1, 1]
        normalized = 2 * (gray / 255.0) - 1
        
        # Apply Hilbert transform for imaginary part
        return hilbert(normalized)
    
    def decode_to_image(self, complex_arr: NDArray[np.complex128], 
                       width: int, height: int) -> bytes:
        """Convert complex array back to image."""
        # Ensure correct size
        if len(complex_arr) != width * height:
            # Resample
            x_old = np.linspace(0, 1, len(complex_arr))
            x_new = np.linspace(0, 1, width * height)
            real_resampled = np.interp(x_new, x_old, complex_arr.real)
            imag_resampled = np.interp(x_new, x_old, complex_arr.imag)
            complex_arr = real_resampled + 1j * imag_resampled
        
        # Magnitude visualization
        arr_2d = complex_arr.reshape(height, width)
        magnitude = np.abs(arr_2d)
        
        # Normalize to [0, 255]
        mag_normalized = 255 * (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-10)
        
        # Create image
        img = Image.fromarray(mag_normalized.astype(np.uint8), mode='L')
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()


class ImageToComplexArrayProcessor:
    """API-compatible wrapper for image processing that bridges the expected interface."""
    
    def __init__(self, n_points: int = 1000):
        self.encoder = ImageComplexEncoder(n_points)
    
    def image_to_complex_1d(self, image_data: bytes, method: str = "luminance") -> NDArray[np.complex128]:
        """Convert image to complex array using specified encoding method."""
        # Map API encoding methods to actual implementation methods
        method_mapping = {
            "luminance": "hilbert",  # Use Hilbert transform for luminance
            "hilbert": "hilbert",
            "rgb_complex": "auto",  # Use auto path-based method for RGB
            "edge": "edge",
            "contour": "contour", 
            "vector": "vector",
            "auto": "auto"
        }
        
        actual_method = method_mapping.get(method, "auto")
        
        if actual_method == "hilbert":
            return self.encoder.encode_with_hilbert(image_data)
        else:
            return self.encoder.encode(image_data, actual_method)
    
    def complex_1d_to_image(self, complex_arr: NDArray[np.complex128], 
                           width: int, height: int, 
                           method: str = "magnitude") -> bytes:
        """Convert complex array back to image using specified visualization method."""
        # For now, only magnitude visualization is implemented
        # Future: could add phase, real, imaginary visualizations based on method parameter
        _ = method  # Acknowledge parameter for future use
        return self.encoder.decode_to_image(complex_arr, width, height)