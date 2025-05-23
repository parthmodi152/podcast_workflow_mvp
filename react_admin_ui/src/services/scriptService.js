import { API_CONFIG } from '../config';

const BASE_URL = API_CONFIG.SCRIPT_SERVICE;
const TTS_BASE_URL = API_CONFIG.TTS_SERVICE;
const AVATAR_BASE_URL = API_CONFIG.AVATAR_SERVICE;
const STITCH_BASE_URL = API_CONFIG.STITCH_SERVICE;

export const scriptService = {
  // Fetch all scripts
  async getScripts(status = null) {
    const url = status ? `${BASE_URL}/scripts?status=${status}` : `${BASE_URL}/scripts`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Error fetching scripts: ${response.statusText}`);
    }
    return response.json();
  },

  // Fetch a specific script with details
  async getScript(scriptId) {
    const response = await fetch(`${BASE_URL}/scripts/${scriptId}`);
    if (!response.ok) {
      throw new Error(`Error fetching script details: ${response.statusText}`);
    }
    return response.json();
  },

  // Create a new script
  async createScript(scriptData) {
    const response = await fetch(`${BASE_URL}/scripts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(scriptData),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create script: ${errorText}`);
    }
    
    return response.json();
  },

  // Generate TTS for a script
  async generateTTS(scriptId) {
    // Call TTS service directly instead of going through script service proxy
    const response = await fetch(`${TTS_BASE_URL}/tts/process-script/${scriptId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `Error generating TTS: ${response.statusText}`);
    }

    return response.json();
  },

  // Update a script line (placeholder for future implementation)
  async updateScriptLine(lineId, newText) {
    try {
      const response = await fetch(`${BASE_URL}/scripts/lines/${lineId}?text=${encodeURIComponent(newText)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating script line:', error);
      throw error;
    }
  },

  // Delete a script
  async deleteScript(scriptId) {
    try {
      const response = await fetch(`${BASE_URL}/scripts/${scriptId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting script:', error);
      throw error;
    }
  },

  // TTS Service Functions
  
  // Process TTS for a single line
  async processSingleLineTTS(lineId) {
    try {
      const response = await fetch(`${TTS_BASE_URL}/tts/process-line/${lineId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error processing line TTS:', error);
      throw error;
    }
  },

  // Get TTS status for a line
  async getLineTTSStatus(lineId) {
    try {
      const response = await fetch(`${TTS_BASE_URL}/tts/line-status/${lineId}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting line TTS status:', error);
      throw error;
    }
  },

  // Get audio URL for a line
  getAudioUrl(lineId) {
    return `${TTS_BASE_URL}/tts/audio/${lineId}`;
  },

  // Avatar Service Functions
  
  // Process frame generation for a single line
  async processSingleLineFrame(lineId) {
    try {
      const response = await fetch(`${AVATAR_BASE_URL}/avatar/generate/${lineId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error processing line frame generation:', error);
      throw error;
    }
  },

  // Get frame generation status for a line
  async getLineFrameStatus(lineId) {
    try {
      const response = await fetch(`${AVATAR_BASE_URL}/avatar/status/${lineId}`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting line frame status:', error);
      throw error;
    }
  },

  // Get video URL for a line
  getVideoUrl(lineId) {
    return `${AVATAR_BASE_URL}/avatar/video/${lineId}`;
  },

  // Stitch Service Functions
  
  // Check if script is ready for stitching
  async checkStitchReadiness(scriptId) {
    try {
      const response = await fetch(`${STITCH_BASE_URL}/stitch/check/${scriptId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error checking stitch readiness:', error);
      throw error;
    }
  },

  // Trigger final video stitching
  async processStitch(scriptId) {
    try {
      const response = await fetch(`${STITCH_BASE_URL}/stitch/process/${scriptId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error processing stitch:', error);
      throw error;
    }
  },

  // Get final video URL for download
  getFinalVideoUrl(scriptId) {
    return `${STITCH_BASE_URL}/stitch/download/${scriptId}`;
  }
}; 