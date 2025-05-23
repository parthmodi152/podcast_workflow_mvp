import { API_CONFIG } from '../config';

// Generate a default placeholder image for characters
export const generateDefaultImage = () => {
  return `data:image/svg+xml,${encodeURIComponent(`
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="120" height="120" fill="#f0f0f0"/>
      <circle cx="60" cy="45" r="15" fill="#d0d0d0"/>
      <path d="M30 90c0-16.569 13.431-30 30-30s30 13.431 30 30" fill="#d0d0d0"/>
    </svg>
  `)}`;
};

// Get image URL with fallback to default
export const getImageUrl = (imagePath, baseUrl = API_CONFIG.VOICE_SERVICE) => {
  if (!imagePath) return generateDefaultImage();
  return `${baseUrl}${imagePath}`;
};

// Handle image error by setting default image
export const handleImageError = (e) => {
  e.target.src = generateDefaultImage();
}; 