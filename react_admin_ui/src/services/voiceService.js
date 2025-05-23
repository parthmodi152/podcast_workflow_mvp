const BASE_URL = 'http://localhost:8001';

export const voiceService = {
  // Fetch all voices/characters
  async getVoices() {
    const response = await fetch(`${BASE_URL}/voices`);
    if (!response.ok) {
      throw new Error(`Error fetching characters: ${response.statusText}`);
    }
    return response.json();
  },

  // Create a new voice/character
  async createVoice(formData) {
    const response = await fetch(`${BASE_URL}/voices`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to create character: ${errorText}`);
    }
    
    return response.json();
  },

  // Update character image
  async updateVoiceImage(voiceId, formData) {
    const response = await fetch(`${BASE_URL}/voices/${voiceId}/image`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Failed to update image: ${errorText}`);
    }

    return response.json();
  },

  // Delete a voice/character (placeholder for future implementation)
  async deleteVoice(voiceId) {
    // Note: Delete endpoint would need to be implemented in voice service
    throw new Error('Delete functionality not yet implemented');
  }
}; 