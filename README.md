# Podcast Workflow MVP - Cloud Edition

This project is a fully cloud-native workflow that turns a questionnaire (or any long-form content) into a video-podcast featuring multiple AI-cloned speakers. It consists of five independent FastAPI microservices deployed on **Render**, with **Supabase** for database and file storage, and a **React admin UI** that can be deployed on **Vercel**.

## 🏗️ Architecture Overview

**Cloud-Native Microservices Architecture:**
- **Backend Services**: 5 FastAPI microservices on Render
- **Database**: PostgreSQL on Supabase
- **File Storage**: Supabase Storage (4 buckets)
- **Frontend**: React admin UI (deployable to Vercel)
- **No Docker/Local Dependencies**: Fully cloud-hosted

## 🎯 Services Overview

1. **Voice Service**: Clones and catalogs voices using **ElevenLabs API**, stores speaker images in Supabase Storage
2. **Script Service**: Generates structured dialogue using **OpenAI API**
3. **TTS Service**: Generates audio per line using **ElevenLabs API**, stores in Supabase Storage
4. **Avatar Service**: Creates talking-head clips using **Hedra API**, downloads from and uploads to Supabase Storage
5. **Stitch Service**: Concatenates clips using **MoviePy**, creates final episodes in Supabase Storage

## 📁 Project Structure

```
podcast_workflow_mvp/
├── voice_service/          # Voice cloning service
│   ├── src/
│   │   ├── main.py         # FastAPI endpoints
│   │   ├── storage.py      # Supabase Storage integration
│   │   └── ...
│   └── pyproject.toml      # Dependencies
├── script_service/         # Script generation service
├── tts_service/           # Text-to-speech service
├── avatar_service/        # Avatar video generation service
├── stitch_service/        # Video stitching service
├── react_admin_ui/        # React frontend (deployable to Vercel)
│   ├── src/
│   │   ├── config.js      # Service URL configuration
│   │   └── ...
│   └── vercel.json        # Vercel deployment config
└── render.yaml           # Render deployment configuration
```

## 🚀 Deployment Setup

### Prerequisites

1. **API Keys**:
   - ElevenLabs API key
   - OpenAI API key
   - Hedra API key

2. **Cloud Accounts**:
   - [Supabase](https://supabase.com) (Database + Storage)
   - [Render](https://render.com) (Backend services)
   - [Vercel](https://vercel.com) (Frontend - optional)

### 1. Supabase Setup

1. Create a new Supabase project
2. Create 4 storage buckets:
   - `speaker-images`
   - `podcast-audio` 
   - `podcast-video`
   - `podcast-final`
3. Get your connection details:
   - Database URL (PostgreSQL connection string)
   - Project URL
   - Anon/Public key

### 2. Render Deployment

1. Fork this repository to your GitHub
2. Connect your GitHub to Render
3. Import the repository - Render will detect `render.yaml`
4. Set environment variables for each service:

**All Services:**
- `DATABASE_URL`: Your Supabase PostgreSQL connection string
- `SUPABASE_URL`: Your Supabase project URL  
- `SUPABASE_KEY`: Your Supabase anon/public key

**Service-Specific:**
- Voice Service: `ELEVEN_API_KEY`
- Script Service: `OPENAI_API_KEY`
- TTS Service: `ELEVEN_API_KEY`
- Avatar Service: `HEDRA_API_KEY`

5. Deploy all 5 services (takes ~5 minutes)

### 3. React Admin UI Setup

**Option A: Local Development**
```bash
cd react_admin_ui
npm install

# For local development (uses localhost)
npm run start:local

# For production testing (uses Render URLs)
npm run start:production
```

**Option B: Deploy to Vercel**
1. Import the repository to Vercel
2. Set **Root Directory** to `react_admin_ui`
3. Deploy
4. Your admin UI will be available at `https://your-app.vercel.app`

## 🔧 Configuration

### React Admin UI Configuration

Update `react_admin_ui/src/config.js` with your actual Render service URLs:

```javascript
const PRODUCTION_URLS = {
  VOICE_SERVICE: 'https://your-voice-service.onrender.com',
  SCRIPT_SERVICE: 'https://your-script-service.onrender.com',
  TTS_SERVICE: 'https://your-tts-service.onrender.com',
  AVATAR_SERVICE: 'https://your-avatar-service.onrender.com',
  STITCH_SERVICE: 'https://your-stitch-service.onrender.com'
};
```

## 📋 Usage Workflow

### 1. Create Voice Clones
- Navigate to **Characters** tab
- Upload audio samples and speaker image
- Voice is cloned via ElevenLabs and image stored in Supabase

### 2. Generate Scripts  
- Navigate to **Scripts** tab
- Create script with title, length, and select speakers
- OpenAI generates dialogue for selected speakers

### 3. Process Audio & Video
- **TTS Processing**: Generate audio for each script line
- **Avatar Processing**: Create talking-head videos 
- Monitor progress in real-time

### 4. Final Episode
- **Stitch Processing**: Combine all videos into final episode
- **Download**: Get completed podcast from **Episodes** tab

## 🌐 API Endpoints

Replace `{service-url}` with your actual Render service URLs.

### Voice Service

**Clone a voice:**
```bash
curl -X POST https://your-voice-service.onrender.com/voices \
  -F "name=Host Voice" \
  -F "speaker_image=@speaker.jpg" \
  -F "files=@sample_audio.mp3"
```

**List voices:**
```bash
curl https://your-voice-service.onrender.com/voices
```

### Script Service

**Create a script:**
```bash
curl -X POST https://your-script-service.onrender.com/scripts \
  -H "Content-Type: application/json" \
  -d '{
  "title": "Why LLMs Matter",
  "length_minutes": 5,
  "speakers": [
    {"role": "host", "voice_id": "voice_id_1"},
    {"role": "guest", "voice_id": "voice_id_2"}
  ]
  }'
```

**Get script status:**
```bash
curl https://your-script-service.onrender.com/scripts/1
```

## 🗄️ Data Flow

1. **Speaker Images** → `speaker-images` bucket
2. **Audio Files** → `podcast-audio` bucket  
3. **Video Clips** → `podcast-video` bucket
4. **Final Episodes** → `podcast-final` bucket
5. **Database** → Supabase PostgreSQL for metadata

## 🐛 Troubleshooting

### Service Issues
- **Cold Starts**: Render free tier services "sleep" - first request may take 30s
- **Logs**: Check individual service logs in Render dashboard
- **Health Checks**: Test endpoints: `https://your-service.onrender.com/health`

### Storage Issues  
- **Bucket Permissions**: Ensure buckets are created and accessible
- **File Uploads**: Check Supabase storage dashboard for uploaded files
- **URLs**: Verify Supabase URLs and keys are correct

### React UI Issues
- **CORS**: Services should handle CORS automatically  
- **Environment**: Check browser console for config debug info
- **Network**: Verify service URLs in `config.js` are correct

### Performance Notes
- **Free Tier Limits**: Render/Supabase free tiers have usage limits
- **Processing Time**: Avatar generation takes 2-5 minutes per clip
- **File Sizes**: Large audio/video files may timeout on free tiers

## 🏆 Production Considerations

For production deployment:
- **Render**: Upgrade to paid plans for better performance
- **Supabase**: Monitor storage usage and upgrade as needed
- **API Limits**: Consider rate limiting for ElevenLabs/OpenAI/Hedra
- **Error Handling**: Implement retry logic for external API calls
- **Monitoring**: Set up alerts for service health and storage usage

## 📚 Technology Stack

- **Backend**: FastAPI, Python 3.10, Poetry
- **Database**: PostgreSQL (Supabase)
- **Storage**: Supabase Storage  
- **APIs**: ElevenLabs, OpenAI, Hedra
- **Deployment**: Render (backend), Vercel (frontend)
- **Frontend**: React, Create React App

## 🔗 External Dependencies

- **ElevenLabs**: Voice cloning and TTS
- **OpenAI**: Script generation
- **Hedra**: Avatar video generation  
- **Supabase**: Database and file storage
- **Render**: Service deployment
- **Vercel**: Frontend deployment (optional)

---

🎬 **Ready to create your first AI podcast?** Deploy the services and start with the Characters tab to clone your first voice!

