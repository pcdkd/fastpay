import { spawn } from 'child_process';
import { EventEmitter } from 'events';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Constants
const RESTART_DELAY_MS = 2000;  // Delay before restarting crashed NFC process
const GRACEFUL_SHUTDOWN_TIMEOUT_MS = 2000;  // Time to wait for SIGTERM before SIGKILL
const DEFAULT_PYTHON_EXECUTABLE = 'python3';

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
    this.buffer = '';  // Buffer for accumulating partial stdout data
    this.restartTimeout = null;  // Track restart timer to prevent race conditions
    this.killTimeout = null;  // Track SIGKILL timeout for graceful shutdown
  }

  /**
   * Start the Python NFC reader process
   */
  start() {
    if (this.process) {
      console.warn('[NFC] Process already running');
      return;
    }

    // Clear any pending restart timeout and reset shutdown flag
    if (this.restartTimeout) {
      clearTimeout(this.restartTimeout);
      this.restartTimeout = null;
    }
    this.isShuttingDown = false;

    const scriptPath = path.join(__dirname, '../scripts/nfc_reader.py');
    const pythonExecutable = this.config.pythonExecutable || DEFAULT_PYTHON_EXECUTABLE;

    if (this.config.debug) {
      console.log('[NFC] Starting NFC reader process...');
      console.log(`[NFC] Script: ${scriptPath}`);
      console.log(`[NFC] Port: ${this.config.nfcPort}`);
      console.log(`[NFC] Python: ${pythonExecutable}`);
    }

    // Build environment variables, conditionally adding optional config
    const env = {
      ...process.env,
      NFC_PORT: this.config.nfcPort,
    };

    if (this.config.nfcBaudRate != null) {
      env.NFC_BAUD_RATE = this.config.nfcBaudRate.toString();
    }
    if (this.config.tapDebounceMs != null) {
      env.NFC_TAP_DEBOUNCE_MS = this.config.tapDebounceMs.toString();
    }

    this.process = spawn(pythonExecutable, [scriptPath], {
      env,
      stdio: ['ignore', 'pipe', 'pipe'],  // stdin, stdout, stderr
    });

    // Parse JSON events from stdout (IPC)
    // Use buffering to handle partial data chunks
    this.process.stdout.on('data', (data) => {
      this.buffer += data.toString();
      let newlineIndex;

      while ((newlineIndex = this.buffer.indexOf('\n')) !== -1) {
        const line = this.buffer.substring(0, newlineIndex).trim();
        this.buffer = this.buffer.substring(newlineIndex + 1);

        if (line) {
          try {
            const event = JSON.parse(line);
            this.handleEvent(event);
          } catch (err) {
            console.error('[NFC] Invalid JSON from Python:', line);
            this.emit('error', {
              message: `Invalid JSON from Python: ${err.message}`,
              fatal: false,
              raw: line,
            });
          }
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
      this.process = null;  // Only place where process is cleared

      // Clear SIGKILL timeout if process exited
      if (this.killTimeout) {
        clearTimeout(this.killTimeout);
        this.killTimeout = null;
      }

      if (this.isShuttingDown) {
        console.log(`[NFC] Python process exited gracefully (signal: ${signal})`);
      } else {
        console.error(`[NFC] Python process exited unexpectedly (code: ${code}, signal: ${signal})`);
        console.error(`[NFC] Unexpected exit, restarting in ${RESTART_DELAY_MS / 1000} seconds...`);
        this.restartTimeout = setTimeout(() => this.start(), RESTART_DELAY_MS);
      }
    });

    // Handle spawn errors
    this.process.on('error', (err) => {
      console.error('[NFC] Failed to start Python process:', err.message);
      this.emit('error', {
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

    // Cancel any pending restart to prevent race condition
    if (this.restartTimeout) {
      clearTimeout(this.restartTimeout);
      this.restartTimeout = null;
    }

    if (this.process) {
      // Set up SIGKILL timeout in case process doesn't respond to SIGTERM
      this.killTimeout = setTimeout(() => {
        if (this.process) {
          console.warn('[NFC] Python process did not exit gracefully, sending SIGKILL');
          this.process.kill('SIGKILL');
        }
      }, GRACEFUL_SHUTDOWN_TIMEOUT_MS);

      this.process.kill('SIGTERM');
      // Don't set process = null here - let exit handler do it
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
