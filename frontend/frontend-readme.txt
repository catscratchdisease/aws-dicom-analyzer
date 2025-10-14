# Frontend

Single-page web application for image upload and analysis results display.

## Overview

The frontend is a static HTML/CSS/JavaScript application that runs entirely in the browser. It provides:
- Drag-and-drop file upload
- Client-side DICOM viewer using Cornerstone.js
- Real-time results polling
- Responsive design

## Files

- **index.html** - Complete application (HTML + CSS + JavaScript)

## Features

### 1. File Upload
- Drag and drop support
- Accepts: JPG, PNG, GIF, DICOM (.dcm)
- Direct browser-to-S3 upload using presigned URLs
- Upload progress indication

### 2. DICOM Viewer
- Client-side rendering using Cornerstone.js
- Interactive controls:
  - Drag to adjust window/level (brightness/contrast)
  - Scroll wheel to zoom
- Instant preview without server processing

### 3. Results Display
- AI-detected objects from AWS Rekognition
- Confidence scores
- Sorted by confidence (highest first)

### 4. Responsive Design
- Works on desktop and mobile
- Modern gradient UI
- Smooth animations

## Configuration

Before deploying, update the API endpoint:

```javascript
// Line 213 in index.html
const API_ENDPOINT = 'https://YOUR-API-GATEWAY-URL.amazonaws.com';
```

Replace `YOUR-API-GATEWAY-URL` with your actual API Gateway endpoint.

## Dependencies

### External Libraries (CDN)
- **Cornerstone.js** (2.6.1) - DICOM image rendering
- **Cornerstone WADO Image Loader** (4.1.3) - DICOM file loading
- **dicomParser** (1.8.13) - DICOM file parsing

All loaded from jsDelivr CDN:
```html
<script src="https://cdn.jsdelivr.net/npm/cornerstone-core@2.6.1/dist/cornerstone.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/cornerstone-wado-image-loader@4.1.3/dist/cornerstoneWADOImageLoader.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dicom-parser@1.8.13/dist/dicomParser.min.js"></script>
```

## Deployment

### Deploy to S3

```bash
# Upload to S3 website bucket
aws s3 cp index.html s3://YOUR-WEBSITE-BUCKET/

# Make public (if not using bucket policy)
aws s3api put-object-acl \
    --bucket YOUR-WEBSITE-BUCKET \
    --key index.html \
    --acl public-read
```

### Enable S3 Static Website Hosting

```bash
aws s3 website s3://YOUR-WEBSITE-BUCKET \
    --index-document index.html
```

### Get Website URL

```bash
echo "http://YOUR-WEBSITE-BUCKET.s3-website-REGION.amazonaws.com"
```

## Testing Locally

You can test the frontend locally, but uploads will fail without proper CORS:

```bash
# Simple HTTP server (Python)
python3 -m http.server 8000

# Or Node.js
npx http-server

# Open browser
open http://localhost:8000
```

**Note:** For full functionality, you need:
1. API Gateway deployed
2. CORS configured on API Gateway
3. S3 CORS configured on upload bucket

## API Integration

### Endpoints Used

**1. Generate Upload URL**
```
POST /request-upload
Body: { fileName: string, fileType: string }
Response: { uploadUrl: string, jobId: string }
```

**2. Get Results**
```
GET /get-results?jobId={id}
Response: { 
  status: string,
  results: object,
  imageUrl: string,
  error: string 
}
```

### Request Flow

```
1. User selects file
   ↓
2. Frontend requests upload URL from API
   ↓
3. Frontend uploads file directly to S3 using presigned URL
   ↓
4. Frontend polls /get-results every 2 seconds
   ↓
5. Display results when status = "complete"
```

## Customization

### Styling

Update CSS in `<style>` section:
```css
/* Change primary color */
background: linear-gradient(135deg, #YOUR-COLOR 0%, #YOUR-COLOR-2 100%);

/* Change button color */
background: #YOUR-COLOR;
```

### Polling Interval

Change polling frequency:
```javascript
// Line ~334
await sleep(2000); // Change from 2000ms (2 seconds)
```

### Max Poll Attempts

Adjust timeout duration:
```javascript
// Line ~330
async function pollForResults(jobId, maxAttempts = 30) {
  // 30 attempts × 2 seconds = 60 seconds total
  // Increase maxAttempts for longer processing times
}
```

## Troubleshooting

### DICOM Viewer Not Loading

**Symptom:** Error: "DICOM viewer libraries not loaded"

**Solutions:**
1. Check internet connection (CDN access)
2. Check browser console for script loading errors
3. Try different CDN:
   ```html
   <!-- Replace jsdelivr with unpkg -->
   <script src="https://unpkg.com/cornerstone-core@2.6.1/dist/cornerstone.min.js"></script>
   ```
4. Host libraries locally on S3

### Upload Fails with 403

**Symptom:** "Failed to upload file"

**Solutions:**
1. Check S3 CORS configuration on upload bucket
2. Verify Content-Type matches in presigned URL
3. Check presigned URL hasn't expired (1 hour default)

### Results Not Appearing

**Symptom:** "Timeout waiting for results"

**Solutions:**
1. Check Lambda 2 (processImage) is running
2. Verify S3 trigger is configured
3. Check CloudWatch logs for errors
4. Increase maxAttempts for longer processing

### CORS Errors

**Symptom:** "blocked by CORS policy"

**Solutions:**
1. Add CORS to API Gateway
2. Add CORS to S3 upload bucket
3. Ensure response headers include Access-Control-Allow-Origin

## Browser Compatibility

Tested and working on:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Performance

### Optimization Tips
1. Use CloudFront CDN for faster delivery
2. Enable Gzip compression on S3
3. Minimize polling frequency
4. Cache static assets

### Load Times
- Initial page load: < 2 seconds
- DICOM rendering: < 1 second (for 512×512 images)
- API round-trip: < 500ms

## Security Considerations

1. **No sensitive data in frontend** - API keys managed server-side
2. **HTTPS only** - Use CloudFront for SSL
3. **Content Security Policy** - Add CSP headers
4. **Input validation** - File type and size checks

## Future Enhancements

Potential features to add:
- [ ] Multi-file upload
- [ ] Progress bar for processing
- [ ] Download results as PDF
- [ ] DICOM metadata display
- [ ] Image comparison (before/after)
- [ ] User authentication
- [ ] Save analysis history

## Contributing

To modify the frontend:
1. Edit `index.html`
2. Test locally
3. Deploy to S3
4. Clear CloudFront cache if using CDN

## Support

For frontend issues:
- Check browser console for errors
- Test with different browsers
- Verify API endpoint is correct
- Check network tab in dev tools