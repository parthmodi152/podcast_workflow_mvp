// Configuration for service URLs
// Update these URLs with your actual Render service URLs

// Check for custom environment variable or default to production if built for production
const useProduction = process.env.REACT_APP_USE_PRODUCTION === 'true' || 
                     process.env.NODE_ENV === 'production';

// For local development
const LOCAL_URLS = {
  VOICE_SERVICE: 'http://localhost:8001',
  SCRIPT_SERVICE: 'http://localhost:8002', 
  TTS_SERVICE: 'http://localhost:8003',
  AVATAR_SERVICE: 'http://localhost:8004',
  STITCH_SERVICE: 'http://localhost:8005'
};

// For production (Render deployment)
const PRODUCTION_URLS = {
  VOICE_SERVICE: 'https://podcast-voice-service.onrender.com',
  SCRIPT_SERVICE: 'https://podcast-script-service.onrender.com',
  TTS_SERVICE: 'https://podcast-tts-service.onrender.com', 
  AVATAR_SERVICE: 'https://podcast-avatar-service.onrender.com',
  STITCH_SERVICE: 'https://podcast-stitch-service.onrender.com'
};

// Use production URLs if specified, otherwise use local URLs
export const API_CONFIG = useProduction ? PRODUCTION_URLS : LOCAL_URLS;

// Debug info (only in development)
if (process.env.NODE_ENV === 'development') {
  console.log('Environment Config:', {
    NODE_ENV: process.env.NODE_ENV,
    REACT_APP_USE_PRODUCTION: process.env.REACT_APP_USE_PRODUCTION,
    useProduction,
    selectedConfig: useProduction ? 'PRODUCTION' : 'LOCAL'
  });
}

export default API_CONFIG; 