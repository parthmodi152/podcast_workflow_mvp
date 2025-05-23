import React, { useState } from 'react';
import { X, Check, AlertCircle, Loader } from 'lucide-react';
import { voiceService } from '../services/voiceService';
import { getImageUrl, handleImageError } from '../utils/imageUtils';

function EditImageModal({ character, onClose, onSuccess }) {
  const [newImage, setNewImage] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!newImage) {
      setError('Please select an image to upload');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('speaker_image', newImage);

      const result = await voiceService.updateVoiceImage(character.voice_id, formData);
      console.log('Image updated successfully:', result);
      onSuccess();
      
    } catch (err) {
      console.error('Failed to update image:', err);
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setNewImage(file);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-small" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Edit Character Image</h3>
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
            <label>Current Image</label>
            <div className="current-image">
              <img 
                src={getImageUrl(character.image_path)}
                alt={character.name}
                onError={handleImageError}
              />
              <p>{character.name}</p>
            </div>
          </div>
          
          <div className="form-group">
            <label htmlFor="newImage">New Image *</label>
            <input
              id="newImage"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handleImageChange}
              required
            />
            <small>Upload a clear portrait image (JPEG, PNG, WebP)</small>
            
            {newImage && (
              <div className="image-preview">
                <img 
                  src={URL.createObjectURL(newImage)} 
                  alt="Preview" 
                />
                <p>Preview of new image</p>
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
              disabled={uploading || !newImage}
            >
              {uploading ? (
                <>
                  <Loader className="spin" size={16} />
                  Updating...
                </>
              ) : (
                <>
                  <Check size={16} />
                  Update Image
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default EditImageModal; 