/**
 * Dummy file storage service.
 * Accepts multipart/form-data, returns upload metadata.
 * No actual storage - just simulates upload and returns metadata.
 */
const express = require('express');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');

const app = express();

// Configure multer for memory storage (no actual file saving)
const upload = multer({ storage: multer.memoryStorage() });

app.post('/upload', upload.single('file'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded' });
    }

    // Extract metadata from the uploaded file
    const fileId = uuidv4();
    const uploadedAt = new Date().toISOString();

    // Get additional form fields
    const filename = req.body.filename || req.file.originalname;
    const description = req.body.description || '';

    // Return upload metadata
    res.json({
        file_id: fileId,
        url: `https://storage.example.com/files/${fileId}`,
        size: req.file.size,
        uploaded_at: uploadedAt,
        filename: filename,
        description: description
    });
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

const PORT = 9900;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Dummy storage service running on port ${PORT}`);
});
