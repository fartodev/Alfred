class AlfredUI {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.messagesContainer = document.getElementById('messagesContainer');
        this.settingsBtn = document.getElementById('settingsBtn');
        this.micBtn = document.getElementById('micBtn');
        this.modeBadge = document.getElementById('modeBadge');
        this.systemLog = document.getElementById('systemLog');
        this.imageInput = document.getElementById('imageInput');
        this.bulkLearnInput = document.getElementById('bulkLearnInput');
        this.imagePreview = document.getElementById('imagePreview');
        
        this.currentMode = 'wake_word';
        this.isRecording = false;
        this.lastShownTranscription = '';
        this.lastShownAlfredResponse = '';
        this.selectedImage = null;
        
        // Web Speech API setup
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.language = 'en-US';
        
        this.setupSpeechRecognition();
        this.init();
    }
    
    setupSpeechRecognition() {
        this.recognition.onstart = () => {
            this.addLog('[MIC]', 'Listening...', 'recording');
        };
        
        this.recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            
            if (event.results[event.results.length - 1].isFinal) {
                this.handleSpeechResult(transcript);
            }
        };
        
        this.recognition.onerror = (event) => {
            this.addLog('[MIC]', `Error: ${event.error}`, 'error');
            this.isRecording = false;
            this.micBtn.style.opacity = '0.7';
        };
        
        this.recognition.onend = () => {
            this.isRecording = false;
            this.micBtn.style.opacity = '0.7';
        };
    }
    
    async handleSpeechResult(transcript) {
        if (!transcript.trim()) return;
        
        this.addLog('[PTT]', `Heard: ${transcript.substring(0, 35)}...`, 'success');
        this.removeWelcome();
        this.addMessage('user', transcript);
        
        // Send to server
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: transcript })
            });
            
            const data = await response.json();
            
            if (data.error) {
                this.addMessage('error', data.error);
                this.addLog('[ERROR]', data.error, 'error');
            } else {
                this.addMessage('alfred', data.alfred);
                this.addLog('[ALFRED]', 'Response sent', 'success');
            }
        } catch (error) {
            this.addMessage('error', 'Connection failed');
            this.addLog('[ERROR]', 'Connection failed', 'error');
        }
    }
    
    init() {
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !this.messageInput.disabled) this.sendMessage();
        });
        
        this.settingsBtn.addEventListener('click', () => this.cycleMode());
        this.micBtn.addEventListener('click', () => this.toggleRecording());
        
        // Image input listener
        this.imageInput.addEventListener('change', (e) => this.handleImageSelect(e));
        
        // Bulk learn input listener
        this.bulkLearnInput.addEventListener('change', (e) => this.handleBulkLearn(e));
        
        this.addLog('[INIT]', 'System initializing...', 'init');
        this.loadHistory();
        this.getGreeting();
        this.updateStatus();
        
        // Poll for updates
        setInterval(() => this.updateStatus(), 1000);
    }
    
    addLog(prefix, message, type = 'info') {
        const logLine = document.createElement('div');
        logLine.className = `log-line ${type}`;
        
        const prefixEl = document.createElement('span');
        prefixEl.className = 'log-prefix';
        prefixEl.textContent = prefix;
        
        const msgEl = document.createElement('span');
        msgEl.textContent = message;
        
        logLine.appendChild(prefixEl);
        logLine.appendChild(msgEl);
        this.systemLog.appendChild(logLine);
        
        this.systemLog.scrollTop = this.systemLog.scrollHeight;
        
        // Keep only last 30 lines
        while (this.systemLog.children.length > 30) {
            this.systemLog.removeChild(this.systemLog.firstChild);
        }
    }
    
    async sendMessage() {
        if (this.currentMode !== 'text') return;
        
        const message = this.messageInput.value.trim();
        
        // If image exists, analyze it AND send text if present
        if (this.selectedImage) {
            const imageText = message; // Capture text before clearing
            this.messageInput.value = '';  // Clear text input
            this.removeWelcome();
            
            // First send text message if present
            if (imageText) {
                this.addMessage('user', imageText);
                this.addLog('[USER]', imageText.substring(0, 40) + (imageText.length > 40 ? '...' : ''), 'info');
            }
            
            // Then analyze image
            this.analyzeImage();
            return;
        }
        
        // Only text message, no image
        if (message) {
            this.messageInput.value = '';
            this.removeWelcome();
            this.addMessage('user', message);
            this.addLog('[USER]', message.substring(0, 40) + (message.length > 40 ? '...' : ''), 'info');
            
            try {
                this.addLog('[AI]', 'Processing...', 'info');
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    this.addMessage('error', data.error);
                    this.addLog('[ERROR]', data.error, 'error');
                } else {
                    this.addMessage('alfred', data.alfred);
                    this.addLog('[ALFRED]', 'Response sent', 'success');
                }
            } catch (error) {
                this.addMessage('error', 'Connection failed');
                this.addLog('[ERROR]', 'Connection failed', 'error');
            }
            return;
        }
    }
    
    
    addMessage(type, text) {
        const message = document.createElement('div');
        message.className = `message ${type}`;
        
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = text;
        
        message.appendChild(bubble);
        this.messagesContainer.appendChild(message);
        
        this.messagesContainer.parentElement.scrollTop = this.messagesContainer.parentElement.scrollHeight;
    }
    
    removeWelcome() {
        const welcome = this.messagesContainer.querySelector('.welcome');
        if (welcome) welcome.remove();
    }
    
    async cycleMode() {
        try {
            const response = await fetch('/api/mode/cycle', { method: 'POST' });
            const data = await response.json();
            
            this.currentMode = data.mode;
            this.updateModeDisplay();
            
            const modeNames = {
                'wake_word': 'Wake Word mode',
                'push_to_talk': 'Push-to-Talk mode',
                'text': 'Text input mode'
            };
            this.addLog('[MODE]', modeNames[this.currentMode], 'info');
        } catch (error) {
            this.addLog('[ERROR]', 'Mode change failed', 'error');
        }
    }
    
    async toggleRecording() {
        if (this.currentMode === 'push_to_talk') {
            if (!this.isRecording) {
                // Start recording using Web Speech API
                this.isRecording = true;
                this.micBtn.style.opacity = '1';
                this.recognition.start();
            } else {
                // Stop recording
                this.isRecording = false;
                this.micBtn.style.opacity = '0.7';
                this.recognition.stop();
            }
        }
    }
    
    updateModeDisplay() {
        const modeText = {
            'wake_word': '🎤 Wake Word',
            'push_to_talk': '🎙️ Push to Talk',
            'text': '⌨️ Text Mode'
        };
        this.modeBadge.textContent = modeText[this.currentMode] || this.currentMode;
        
        // Enable/disable input based on mode
        if (this.currentMode === 'text') {
            this.messageInput.disabled = false;
            this.messageInput.style.opacity = '1';
        } else {
            this.messageInput.disabled = true;
            this.messageInput.style.opacity = '0.5';
        }
    }
    
    async loadHistory() {
        try {
            const response = await fetch('/api/history?limit=5');
            const data = await response.json();
            
            if (data && data.length > 0) {
                this.removeWelcome();
                data.forEach(msg => {
                    this.addMessage('user', msg.user);
                    this.addMessage('alfred', msg.alfred);
                });
            }
        } catch (error) {
            // Silent
        }
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            this.currentMode = data.mode;
            this.updateModeDisplay();
            
            // Check for new wake word transcriptions
            if (this.currentMode === 'wake_word' && data.last_transcription && data.last_transcription !== this.lastShownTranscription) {
                this.lastShownTranscription = data.last_transcription;
                
                this.removeWelcome();
                this.addMessage('user', data.last_transcription);
                this.addLog('[WAKE]', data.last_transcription.substring(0, 35) + '...', 'success');
                
                // Auto-load Alfred's response from history (wait a moment for it to save)
                setTimeout(async () => {
                    try {
                        const historyResp = await fetch('/api/history?limit=1');
                        const history = await historyResp.json();
                        if (history && history.length > 0) {
                            const latestMsg = history[0];
                            if (latestMsg.user === data.last_transcription && latestMsg.alfred) {
                                this.addMessage('alfred', latestMsg.alfred);
                                this.addLog('[ALFRED]', 'Response received', 'success');
                            }
                        }
                    } catch (e) {
                        // Silent
                    }
                }, 500);
            }
            
            // Check for push-to-talk transcriptions and responses
            if (this.currentMode === 'push_to_talk' && data.ppt_transcription && data.ppt_transcription !== this.lastShownTranscription) {
                this.lastShownTranscription = data.ppt_transcription;
                this.lastShownAlfredResponse = '';
                
                this.removeWelcome();
                this.addMessage('user', data.ppt_transcription);
                this.addLog('[PTT]', data.ppt_transcription.substring(0, 35) + '...', 'info');
            }
            
            // Check if PTT response is ready - fetch and display
            if (this.currentMode === 'push_to_talk' && data.ppt_response_ready && data.ppt_transcription && data.ppt_transcription === this.lastShownTranscription) {
                try {
                    const historyResp = await fetch('/api/history?limit=1');
                    const history = await historyResp.json();
                    if (history && history.length > 0) {
                        const latestMsg = history[0];
                        // Show Alfred's response if it's new and matches current transcription
                        if (latestMsg.user === data.ppt_transcription && latestMsg.alfred && latestMsg.alfred !== this.lastShownAlfredResponse) {
                            this.lastShownAlfredResponse = latestMsg.alfred;
                            this.addMessage('alfred', latestMsg.alfred);
                            this.addLog('[ALFRED]', 'Response received', 'success');
                        }
                    }
                } catch (e) {
                    // Silent
                }
            }
        } catch (error) {
            // Silent polling
        }
    }
    
    async getGreeting() {
        try {
            const response = await fetch('/api/greeting');
            const data = await response.json();
            
            if (data.greeting) {
                this.removeWelcome();
                this.addMessage('alfred', data.greeting);
                this.addLog('[READY]', `System ready - ${data.conversation_count} memories`, 'success');
            } else if (data.conversation_count) {
                this.addLog('[READY]', `System ready - ${data.conversation_count} memories`, 'success');
            }
        } catch (error) {
            this.addLog('[READY]', 'System ready', 'success');
        }
    }
    
    handleImageSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            this.selectedImage = e.target.result; // base64
            this.showImagePreview(file.name);
            this.addLog('[IMAGE]', 'Image selected for analysis', 'info');
        };
        reader.readAsDataURL(file);
    }
    
    showImagePreview(fileName) {
        this.imagePreview.innerHTML = '';
        const previewItem = document.createElement('div');
        previewItem.className = 'image-preview-item';
        
        const img = document.createElement('img');
        img.src = this.selectedImage;
        img.alt = fileName;
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-image';
        removeBtn.textContent = '✕';
        removeBtn.addEventListener('click', () => this.clearImage());
        
        previewItem.appendChild(img);
        previewItem.appendChild(removeBtn);
        this.imagePreview.appendChild(previewItem);
    }
    
    clearImage() {
        this.selectedImage = null;
        this.imagePreview.innerHTML = '';
        this.imageInput.value = '';
        this.addLog('[IMAGE]', 'Image cleared', 'info');
    }
    
    async analyzeImage() {
        if (!this.selectedImage) return;
        
        this.addLog('[IMAGE]', 'Sending to LLaVA for analysis...', 'info');
        
        try {
            const response = await fetch('/api/analyze-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: this.selectedImage })
            });
            
            const data = await response.json();
            
            if (data.error) {
                this.addMessage('error', `Analysis failed: ${data.error}`);
                this.addLog('[ERROR]', data.error, 'error');
            } else {
                this.removeWelcome();
                // Show image analysis from LLaVA
                this.addMessage('system', `📷 Image Analysis:\n${data.analysis}`);
                // Show Alfred's response
                if (data.alfred_response) {
                    this.addMessage('alfred', data.alfred_response);
                    this.addLog('[IMAGE]', 'Analysis complete', 'success');
                } else {
                    this.addLog('[IMAGE]', 'Analysis complete but no response', 'warning');
                }
                this.clearImage();
            }
        } catch (error) {
            this.addMessage('error', 'Analysis connection failed');
            this.addLog('[ERROR]', 'Connection failed', 'error');
        }
    }

    async handleBulkLearn(event) {
        const file = event.target.files[0];
        if (!file) return;

        this.addLog('[BULK]', `Learning from ${file.name}...`, 'info');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/bulk-learn', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.error) {
                this.addMessage('error', `Bulk learn failed: ${data.error}`);
                this.addLog('[BULK]', `Error: ${data.error}`, 'error');
            } else {
                this.addMessage('system', `📚 Learned ${data.learned} Q&A pairs from ${file.name}. Total conversations: ${data.total_conversations}`);
                this.addLog('[BULK]', `Successfully learned ${data.learned} Q&A pairs!`, 'success');
                
                if (data.errors && data.errors.length > 0) {
                    this.addLog('[BULK]', `Warnings: ${data.errors.length} lines had issues`, 'warning');
                }
            }
        } catch (error) {
            this.addMessage('error', 'Bulk learn connection failed');
            this.addLog('[ERROR]', 'Connection failed', 'error');
        } finally {
            // Reset file input
            this.bulkLearnInput.value = '';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AlfredUI();
});
