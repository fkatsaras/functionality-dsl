/**
 * Dummy text storage service.
 * Accepts text/plain, echoes it back (simulating storage/retrieval).
 * No business logic - just simulates receiving and returning text.
 */
const express = require('express');
const app = express();

// Middleware to handle text/plain
app.use(express.text({ type: 'text/plain' }));

app.post('/transform', (req, res) => {
    if (req.get('Content-Type') !== 'text/plain') {
        return res.status(400).type('text/plain').send('Expected text/plain');
    }

    // Get the plain text from request body
    const text = req.body;

    // Dummy service just echoes back the text (simulating storage/retrieval)
    // Business logic (uppercase, censoring, etc.) is handled in the DSL
    res.type('text/plain').send(text);
});

app.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

const PORT = 9800;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Dummy text service running on port ${PORT}`);
});
