"""Image filter implementations.

This module provides various image processing filters:
- Blur and sharpen
- Brightness and contrast adjustment
- Hue and saturation adjustment
- And more
"""

from PIL import Image, ImageFilter, ImageEnhance
import numpy as np


class Filters:
    """Collection of image filter methods."""
    
    @staticmethod
    def blur(image: Image.Image, radius: int = 2) -> Image.Image:
        """Apply Gaussian blur filter.
        
        Args:
            image: Input PIL Image
            radius: Blur radius (higher = more blur)
            
        Returns:
            Blurred image
        """
        return image.filter(ImageFilter.GaussianBlur(radius=radius))
    
    @staticmethod
    def sharpen(image: Image.Image, factor: float = 1.5) -> Image.Image:
        """Apply sharpen filter.
        
        Args:
            image: Input PIL Image
            factor: Sharpening factor (1.0 = no change, >1.0 = sharper)
            
        Returns:
            Sharpened image
        """
        enhancer = ImageEnhance.Sharpness(image)
        return enhancer.enhance(factor)
    
    @staticmethod
    def adjust_brightness(image: Image.Image, factor: float) -> Image.Image:
        """Adjust image brightness.
        
        Args:
            image: Input PIL Image
            factor: Brightness factor (1.0 = no change, <1.0 = darker, >1.0 = brighter)
            
        Returns:
            Adjusted image
        """
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(factor)
    
    @staticmethod
    def adjust_contrast(image: Image.Image, factor: float) -> Image.Image:
        """Adjust image contrast.
        
        Args:
            image: Input PIL Image
            factor: Contrast factor (1.0 = no change, <1.0 = less contrast, >1.0 = more contrast)
            
        Returns:
            Adjusted image
        """
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(factor)
    
    @staticmethod
    def adjust_hue_saturation(image: Image.Image, hue_shift: int = 0, saturation: float = 1.0) -> Image.Image:
        """Adjust hue and saturation.
        
        Args:
            image: Input PIL Image
            hue_shift: Hue shift in degrees (-180 to 180)
            saturation: Saturation multiplier (1.0 = no change, 0.0 = grayscale, >1.0 = more saturated)
            
        Returns:
            Adjusted image
        """
        # Convert to RGB for processing
        has_alpha = image.mode == 'RGBA'
        if has_alpha:
            alpha = image.split()[3]
            image = image.convert('RGB')
        else:
            image = image.convert('RGB')
        
        # Convert to HSV
        img_array = np.array(image, dtype=np.float32) / 255.0
        
        # RGB to HSV conversion
        r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]
        max_c = np.maximum(np.maximum(r, g), b)
        min_c = np.minimum(np.minimum(r, g), b)
        diff = max_c - min_c
        
        # Hue calculation
        h = np.zeros_like(max_c)
        mask = diff != 0
        
        r_mask = mask & (max_c == r)
        g_mask = mask & (max_c == g)
        b_mask = mask & (max_c == b)
        
        h[r_mask] = (60 * ((g[r_mask] - b[r_mask]) / diff[r_mask]) + 360) % 360
        h[g_mask] = (60 * ((b[g_mask] - r[g_mask]) / diff[g_mask]) + 120) % 360
        h[b_mask] = (60 * ((r[b_mask] - g[b_mask]) / diff[b_mask]) + 240) % 360
        
        # Saturation calculation
        s = np.zeros_like(max_c)
        s[max_c != 0] = diff[max_c != 0] / max_c[max_c != 0]
        
        # Value
        v = max_c
        
        # Apply adjustments
        h = (h + hue_shift) % 360
        s = np.clip(s * saturation, 0, 1)
        
        # Convert back to RGB
        h_i = (h / 60).astype(np.int32) % 6
        f = h / 60 - h_i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        
        r_new = np.zeros_like(v)
        g_new = np.zeros_like(v)
        b_new = np.zeros_like(v)
        
        mask0 = h_i == 0
        mask1 = h_i == 1
        mask2 = h_i == 2
        mask3 = h_i == 3
        mask4 = h_i == 4
        mask5 = h_i == 5
        
        r_new[mask0], g_new[mask0], b_new[mask0] = v[mask0], t[mask0], p[mask0]
        r_new[mask1], g_new[mask1], b_new[mask1] = q[mask1], v[mask1], p[mask1]
        r_new[mask2], g_new[mask2], b_new[mask2] = p[mask2], v[mask2], t[mask2]
        r_new[mask3], g_new[mask3], b_new[mask3] = p[mask3], q[mask3], v[mask3]
        r_new[mask4], g_new[mask4], b_new[mask4] = t[mask4], p[mask4], v[mask4]
        r_new[mask5], g_new[mask5], b_new[mask5] = v[mask5], p[mask5], q[mask5]
        
        # Create result image
        result = np.stack([r_new, g_new, b_new], axis=2)
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        result_image = Image.fromarray(result, 'RGB')
        
        # Restore alpha if needed
        if has_alpha:
            result_image = result_image.convert('RGBA')
            result_image.putalpha(alpha)
        
        return result_image
    
    @staticmethod
    def desaturate(image: Image.Image) -> Image.Image:
        """Remove color (convert to grayscale). Same as grayscale for RGBA."""
        return Filters.grayscale(image)
    
    @staticmethod
    def grayscale(image: Image.Image) -> Image.Image:
        """Convert image to grayscale.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Grayscale image
        """
        has_alpha = image.mode == 'RGBA'
        if has_alpha:
            alpha = image.split()[3]
            gray = image.convert('L').convert('RGB')
            result = gray.convert('RGBA')
            result.putalpha(alpha)
            return result
        else:
            return image.convert('L').convert('RGB')
    
    @staticmethod
    def invert(image: Image.Image) -> Image.Image:
        """Invert image colors.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Inverted image
        """
        has_alpha = image.mode == 'RGBA'
        if has_alpha:
            r, g, b, a = image.split()
            rgb = Image.merge('RGB', (r, g, b))
            inverted_rgb = ImageEnhance.Color(rgb).enhance(0)
            inverted_rgb = Image.eval(rgb, lambda x: 255 - x)
            result = Image.merge('RGBA', (*inverted_rgb.split(), a))
            return result
        else:
            rgb = image.convert('RGB')
            return Image.eval(rgb, lambda x: 255 - x)
    
    @staticmethod
    def edge_detect(image: Image.Image) -> Image.Image:
        """Apply edge detection filter.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Edge-detected image
        """
        has_alpha = image.mode == 'RGBA'
        if has_alpha:
            alpha = image.split()[3]
            rgb = image.convert('RGB')
            edges = rgb.filter(ImageFilter.FIND_EDGES)
            result = edges.convert('RGBA')
            result.putalpha(alpha)
            return result
        else:
            return image.convert('RGB').filter(ImageFilter.FIND_EDGES)
    
    @staticmethod
    def sepia(image: Image.Image) -> Image.Image:
        """Apply sepia tone filter.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Sepia-toned image
        """
        img = image.convert('RGB')
        arr = np.array(img)
        # Sepia matrix
        r = arr[:, :, 0]
        g = arr[:, :, 1]
        b = arr[:, :, 2]
        tr = (0.393 * r + 0.769 * g + 0.189 * b).clip(0, 255).astype(np.uint8)
        tg = (0.349 * r + 0.686 * g + 0.168 * b).clip(0, 255).astype(np.uint8)
        tb = (0.272 * r + 0.534 * g + 0.131 * b).clip(0, 255).astype(np.uint8)
        out = np.stack([tr, tg, tb], axis=2)
        result = Image.fromarray(out)
        if image.mode == 'RGBA':
            result = result.convert('RGBA')
            result.putalpha(image.split()[3])
        return result
    
    @staticmethod
    def posterize(image: Image.Image, bits: int = 4) -> Image.Image:
        """Reduce number of bits per channel (posterize effect).
        
        Args:
            image: Input PIL Image
            bits: Bits per channel (2-8). Lower = fewer colors, more poster-like.
            
        Returns:
            Posterized image
        """
        bits = max(2, min(8, bits))
        out = Image.eval(image, lambda x: (x >> (8 - bits)) << (8 - bits))
        return out.convert(image.mode)
    
    @staticmethod
    def make_color_transparent(
        image: Image.Image, target_r: int, target_g: int, target_b: int, tolerance: int = 30
    ) -> Image.Image:
        """Make pixels matching the target color (within tolerance) transparent.
        
        Args:
            image: Input PIL Image (RGBA or RGB)
            target_r, target_g, target_b: Color to make transparent (0-255)
            tolerance: How close a pixel must be to the target (0-255). Max of channel differences.
            
        Returns:
            Image with matching pixels made transparent
        """
        img = image.convert('RGBA')
        arr = np.array(img)
        r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
        dr = np.abs(r.astype(np.int32) - target_r)
        dg = np.abs(g.astype(np.int32) - target_g)
        db = np.abs(b.astype(np.int32) - target_b)
        match = (dr <= tolerance) & (dg <= tolerance) & (db <= tolerance)
        a_new = np.where(match, 0, a)
        arr[:, :, 3] = a_new
        return Image.fromarray(arr)
    
    @staticmethod
    def emboss(image: Image.Image) -> Image.Image:
        """Apply emboss filter (raised/engraved effect).
        
        Args:
            image: Input PIL Image (RGBA or RGB)
            
        Returns:
            Embossed image
        """
        return image.filter(ImageFilter.EMBOSS)
    
    @staticmethod
    def smooth(image: Image.Image) -> Image.Image:
        """Apply smooth filter (soften/smooth image).
        
        Args:
            image: Input PIL Image (RGBA or RGB)
            
        Returns:
            Smoothed image
        """
        return image.filter(ImageFilter.SMOOTH)
    
    @staticmethod
    def detail(image: Image.Image) -> Image.Image:
        """Apply detail filter (enhance fine details).
        
        Args:
            image: Input PIL Image (RGBA or RGB)
            
        Returns:
            Detail-enhanced image
        """
        return image.filter(ImageFilter.DETAIL)
