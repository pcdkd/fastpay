import { spawn } from 'child_process';
import { EventEmitter } from 'events';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * NFC Bridge - Manages Python NFC reader process and IPC
 *
 * This class spawns the Python nfc_reader.py script as a child process
 * and parses JSON events from stdout for tap detection.
 *
 * Events:
 *  - ready: NFC reader initialized successfully
 *  - tap: Phone/tag detected (includes UID)
 *  - error: Hardware or communication error
 *  - shutdown: Graceful shutdown initiated
 *  - heartbeat: Process alive signal (every 30s)
 *
 * Usage:
 *   const nfc = new NFCBridge(config);
 *   nfc.on('ready', () => console.log('NFC ready'));
 *   nfc.on('tap', ({ uid }) => console.log('Tap:', uid));
 *   nfc.start();
 */
export class NFCBridge extends EventEmitter {
  constructor(config) {
    super();
    this.config = config;
    this.process = null;
    this.isShuttingDown = false;
  }

  /**
   * Start the Python NFC reader process
   */
  start() {
    if (this.process) {
      console.warn('[NFC] Process already running');
      return;
    }

    const scriptPath = path.join(__dirname, '../scripts/nfc_reader.py');

    console.log('[NFC] Starting NFC reader process...');
    console.log(`[NFC] Script: ${scriptPath}`);
    console.log(`[NFC] Port: ${this.config.nfcPort}`);

    this.process = spawn('python3', [scriptPath], {
      env: {
        ...process.env,
        NFC_PORT: this.config.nfcPort,
        NFC_BAUD_RATE: this.config.nfcBaudRate.toString(),
        NFC_TAP_DEBOUNCE_MS: this.config.tapDebounceMs.toString(),
      },
      stdio: ['ignore', 'pipe', 'pipe'],  // stdin, stdout, stderr
    });

    // Parse JSON events from stdout (IPC)
    this.process.stdout.on('data', (data) => {
      const lines = data.toString().split('\n').filter(line => line.trim());

      for (const line of lines) {
        try {
          const event = JSON.parse(line);
          this.handleEvent(event);
        } catch (err) {
          console.error('[NFC] Invalid JSON from Python:', line);
        }
      }
    });

    // Log stderr (debug output from Python)
    this.process.stderr.on('data', (data) => {
      const message = data.toString().trim();
      if (message) {
        console.error('[NFC Debug]', message);
      }
    });

    // Handle process exit
    this.process.on('exit', (code, signal) => {
      console.error(`[NFC] Python process exited (code: ${code}, signal: ${signal})`);

      if (!this.isShuttingDown) {
        console.error('[NFC] Unexpected exit, restarting in 2 seconds...');
        this.process = null;
        setTimeout(() => this.start(), 2000);
      } else {
        this.process = null;
      }
    });

    // Handle spawn errors
    this.process.on('error', (err) => {
      console.error('[NFC] Failed to start Python process:', err.message);
      this.emit('error', {
        event: 'error',
        message: `Failed to start NFC reader: ${err.message}`,
        fatal: true,
      });
    });

    console.log('[NFC] Bridge started, waiting for PN532...');
  }

  /**
   * Stop the NFC reader process
   */
  stop() {
    console.log('[NFC] Stopping NFC reader...');
    this.isShuttingDown = true;

    if (this.process) {
      this.process.kill('SIGTERM');
      this.process = null;
    }
  }

  /**
   * Handle events from Python process
   */
  handleEvent(event) {
    const { event: eventType, ...data } = event;

    switch (eventType) {
      case 'ready':
        console.log(`[NFC] Reader ready - Firmware v${data.firmware} on ${data.port}`);
        this.emit('ready', data);
        break;

      case 'tap':
        console.log(`[NFC] Tap detected: ${data.uid}`);
        this.emit('tap', data);
        break;

      case 'error':
        console.error(`[NFC] Error: ${data.message} (fatal: ${data.fatal})`);
        this.emit('error', data);
        break;

      case 'shutdown':
        console.log(`[NFC] Shutdown: ${data.reason}`);
        this.emit('shutdown', data);
        break;

      case 'heartbeat':
        // Silent heartbeat (just emit event, no logging)
        this.emit('heartbeat', data);
        break;

      default:
        console.warn(`[NFC] Unknown event type: ${eventType}`, data);
    }
  }
}
