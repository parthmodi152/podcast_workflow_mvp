import React, { useState } from 'react';
import { Upload, X, Check, AlertCircle, Loader } from 'lucide-react';
import { voiceService } from '../services/voiceService';

function CreateCharacterModal({ onClose, onSuccess }) {
  const [formData, setFormData] = useState({
    name: '',
    audioFiles: [],
    image: null
  });
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name.trim()) {
      setError('Character name is required');
      return;
    }
    
    if (formData.audioFiles.length === 0) {
      setError('At least one audio file is required');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const submitData = new FormData();
      submitData.append('name', formData.name);
      
      // Add audio files
      formData.audioFiles.forEach(file => {
        submitData.append('files', file);
      });
      
      // Add image if provided
      if (formData.image) {
        submitData.append('speaker_image', formData.image);
      }

      const result = await voiceService.createVoice(submitData);
      console.log('Character created successfully:', result);
      onSuccess();
      
    } catch (err) {
      console.error('Failed to create character:', err);
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleAudioDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    
    const files = Array.from(e.dataTransfer.files).filter(file => 
      file.type === 'audio/mpeg' || file.type === 'audio/wav'
    );
    
    if (files.length > 0) {
      setFormData(prev => ({
        ...prev,
        audioFiles: [...prev.audioFiles, ...files]
      }));
    }
  };

  const handleAudioFileChange = (e) => {
    const files = Array.from(e.target.files);
    setFormData(prev => ({
      ...prev,
      audioFiles: [...prev.audioFiles, ...files]
    }));
  };

  const removeAudioFile = (index) => {
    setFormData(prev => ({
      ...prev,
      audioFiles: prev.audioFiles.filter((_, i) => i !== index)
    }));
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setFormData(prev => ({ ...prev, image: file }));
    }
  };
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create New Character</h3>
          <button className="btn-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          {error && (
            <div className="alert alert-error">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="characterName">Character Name *</label>
            <input 
              id="characterName"
              type="text" 
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder="e.g., John Doe, Sarah Smith"
              required 
            />
          </div>

          <div className="form-group">
            <label htmlFor="characterImage">Character Image</label>
            <input 
              id="characterImage"
              type="file" 
              accept="image/jpeg,image/png,image/webp"
              onChange={handleImageChange}
            />
            <small>Upload a clear portrait image for the character (optional)</small>
            {formData.image && (
              <div className="image-preview">
                <img 
                  src={URL.createObjectURL(formData.image)} 
                  alt="Preview" 
                />
                <button 
                  type="button" 
                  onClick={() => setFormData(prev => ({ ...prev, image: null }))}
                >
                  Remove
                </button>
              </div>
            )}
          </div>
          
          <div className="form-group">
            <label>Audio Files *</label>
            <div 
              className={`file-drop-zone ${dragActive ? 'active' : ''}`}
              onDragEnter={(e) => { e.preventDefault(); setDragActive(true); }}
              onDragLeave={(e) => { e.preventDefault(); setDragActive(false); }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleAudioDrop}
            >
              <Upload size={32} />
              <p>Drag & drop audio files here, or click to select</p>
              <input 
                type="file" 
                multiple 
                accept=".mp3,.wav,audio/mpeg,audio/wav"
                onChange={handleAudioFileChange}
                style={{ display: 'none' }}
                id="audioInput"
              />
              <label htmlFor="audioInput" className="btn-secondary">
                Select Audio Files
              </label>
            </div>
            <small>Upload 1-2 minutes of clean, single-speaker audio for best results (MP3 or WAV)</small>

            {formData.audioFiles.length > 0 && (
              <div className="file-list">
                {formData.audioFiles.map((file, index) => (
                  <div key={index} className="file-item">
                    <span>{file.name}</span>
                    <button 
                      type="button" 
                      onClick={() => removeAudioFile(index)}
                      className="btn-icon btn-delete"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-primary" 
              disabled={uploading || !formData.name.trim() || formData.audioFiles.length === 0}
            >
              {uploading ? (
                <>
                  <Loader className="spin" size={16} />
                  Creating...
                </>
              ) : (
                <>
                  <Check size={16} />
                  Create Character
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CreateCharacterModal; 