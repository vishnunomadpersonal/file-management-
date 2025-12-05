const express = require('express');
const multer = require('multer');
const net = require('net');
const fs = require('fs');
const path = require('path');

const app = express();
const port = 3000;

// Configuration
const CLAMD_HOST = process.env.CLAMD_HOST || 'clamav';
const CLAMD_PORT = parseInt(process.env.CLAMD_PORT) || 3310;

// Configure multer for file uploads
const upload = multer({ dest: '/tmp/uploads/' });

// Ensure upload directory exists
const uploadDir = '/tmp/uploads/';
if (!fs.existsSync(uploadDir)) {
    fs.mkdirSync(uploadDir, { recursive: true });
}

// Function to connect to ClamAV daemon
function scanFile(filePath) {
    return new Promise((resolve, reject) => {
        const client = new net.Socket();
        
        client.setTimeout(30000); // 30 second timeout
        
        client.connect(CLAMD_PORT, CLAMD_HOST, () => {
            console.log(`Connected to ClamAV at ${CLAMD_HOST}:${CLAMD_PORT}`);
            
            // Send INSTREAM command
            client.write('zINSTREAM\0');
            
            // Read file and send in chunks
            const fileStream = fs.createReadStream(filePath);
            
            fileStream.on('data', (chunk) => {
                // Send chunk size (4 bytes, network byte order) followed by chunk
                const sizeBuffer = Buffer.alloc(4);
                sizeBuffer.writeUInt32BE(chunk.length, 0);
                client.write(sizeBuffer);
                client.write(chunk);
            });
            
            fileStream.on('end', () => {
                // Send zero-length chunk to indicate end
                const endBuffer = Buffer.alloc(4);
                endBuffer.writeUInt32BE(0, 0);
                client.write(endBuffer);
            });
            
            fileStream.on('error', (err) => {
                client.destroy();
                reject(new Error(`File read error: ${err.message}`));
            });
        });
        
        let responseData = '';
        
        client.on('data', (data) => {
            responseData += data.toString();
        });
        
        client.on('end', () => {
            const response = responseData.trim();
            console.log('ClamAV response:', response);
            
            if (response.includes('FOUND')) {
                const virusName = response.split(': ')[1].replace(' FOUND', '');
                resolve({
                    is_infected: true,
                    virus_name: virusName,
                    result: 'FOUND',
                    raw_response: response
                });
            } else if (response.includes('OK')) {
                resolve({
                    is_infected: false,
                    virus_name: null,
                    result: 'OK',
                    raw_response: response
                });
            } else {
                resolve({
                    is_infected: null,
                    virus_name: null,
                    result: 'ERROR',
                    raw_response: response,
                    error: 'Unexpected ClamAV response'
                });
            }
        });
        
        client.on('error', (err) => {
            reject(new Error(`ClamAV connection error: ${err.message}`));
        });
        
        client.on('timeout', () => {
            client.destroy();
            reject(new Error('ClamAV connection timeout'));
        });
    });
}

// Function to test ClamAV connection
function testClamAVConnection() {
    return new Promise((resolve, reject) => {
        const client = new net.Socket();
        
        client.setTimeout(5000);
        
        client.connect(CLAMD_PORT, CLAMD_HOST, () => {
            client.write('zPING\0');
        });
        
        client.on('data', (data) => {
            const response = data.toString().trim();
            client.destroy();
            
            // Fix: Use includes instead of exact match
            if (response.includes('PONG')) {
                resolve(true);
            } else {
                reject(new Error(`Unexpected ping response: ${response}`));
            }
        });
        
        client.on('error', (err) => {
            reject(err);
        });
        
        client.on('timeout', () => {
            client.destroy();
            reject(new Error('Connection timeout'));
        });
    });
}

// Middleware to log requests
app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
    next();
});

// Health check endpoint
app.get('/', async (req, res) => {
    try {
        await testClamAVConnection();
        res.json({ 
            status: 'healthy',
            message: 'ClamAV REST API is running and connected to ClamAV daemon',
            clamd_host: CLAMD_HOST,
            clamd_port: CLAMD_PORT
        });
    } catch (error) {
        res.status(503).json({ 
            status: 'unhealthy',
            message: 'Cannot connect to ClamAV daemon',
            error: error.message,
            clamd_host: CLAMD_HOST,
            clamd_port: CLAMD_PORT
        });
    }
});

// Scan file endpoint
app.post('/scan', upload.single('file'), async (req, res) => {
    if (!req.file) {
        return res.status(400).json({ 
            error: 'No file uploaded',
            is_infected: null,
            virus_name: null,
            result: 'ERROR'
        });
    }

    const filePath = req.file.path;
    console.log(`Scanning file: ${req.file.originalname} (${req.file.size} bytes)`);

    try {
        const scanResult = await scanFile(filePath);
        
        // Clean up uploaded file
        fs.unlinkSync(filePath);
        
        res.json(scanResult);
        
    } catch (error) {
        console.error('Scan error:', error.message);
        
        // Clean up uploaded file
        try {
            fs.unlinkSync(filePath);
        } catch (cleanupError) {
            console.error('Cleanup error:', cleanupError.message);
        }
        
        res.status(500).json({ 
            error: error.message,
            is_infected: null,
            virus_name: null,
            result: 'ERROR'
        });
    }
});

// Ping endpoint for ClamAV daemon
app.get('/ping', async (req, res) => {
    try {
        await testClamAVConnection();
        res.json({ status: 'PONG', message: 'ClamAV daemon is responding' });
    } catch (error) {
        res.status(503).json({ 
            status: 'ERROR', 
            message: 'ClamAV daemon not responding',
            error: error.message
        });
    }
});

// Start server
app.listen(port, '0.0.0.0', () => {
    console.log(`ClamAV REST API server listening on port ${port}`);
    console.log(`Will connect to ClamAV at ${CLAMD_HOST}:${CLAMD_PORT}`);
    
    // Test initial connection
    testClamAVConnection()
        .then(() => {
            console.log('✅ Successfully connected to ClamAV daemon');
        })
        .catch((error) => {
            console.log('⚠️  Cannot connect to ClamAV daemon yet:', error.message);
            console.log('   Will retry when requests come in...');
        });
});