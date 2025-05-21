document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    let webSocket = null;
    let isProcessing = false;
    const messageCache = new Map(); // チャットメッセージのキャッシュ
    
    // WebSocketの初期化とイベントハンドリング
    function initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
        
        webSocket = new WebSocket(wsUrl);
        
        webSocket.onopen = () => {
            console.log('WebSocket接続が確立されました');
        };
        
        webSocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleIncomingMessage(data);
        };
        
        webSocket.onclose = () => {
            console.log('WebSocket接続が閉じられました');
            // 再接続を試みる
            setTimeout(initWebSocket, 3000);
        };
        
        webSocket.onerror = (error) => {
            console.error('WebSocketエラー:', error);
        };
    }
    
    // ストリーミングメッセージの処理
    function handleIncomingMessage(data) {
        const { message, is_user, is_streaming, deliberations, thoughts, timestamp, id } = data;
        const messageId = id || `msg-${Date.now()}`;
        
        // 既存のメッセージ要素を探す
        let messageElement = document.getElementById(messageId);
        
        if (!messageElement) {
            // 新しいメッセージ要素を作成
            messageElement = createMessageElement(message, is_user, messageId);
            chatMessages.appendChild(messageElement);
            scrollToBottom();
            
            // メッセージに思考過程パネルがある場合は追加（ストリーミング中に表示）
            if (thoughts && thoughts.length > 0 && !is_user && is_streaming) {
                addThoughtPanel(messageElement, thoughts, message, messageId, true);
            }
            // 互換性のためdeliberationsも処理
            else if (deliberations && deliberations.length > 0 && !is_user) {
                addDeliberationPanel(messageElement, deliberations, messageId);
            }
        } else {
            // 既存のメッセージを更新
            const contentElement = messageElement.querySelector('.message-content');
            contentElement.innerHTML = marked.parse(message);
            
            // 思考過程の更新
            if (thoughts && thoughts.length > 0 && !is_user) {
                updateThoughtPanel(messageId, thoughts, message);
            }
            // 互換性のためdeliberationsも処理
            else if (deliberations && deliberations.length > 0 && !is_user) {
                updateDeliberationPanel(messageId, deliberations);
            }
        }
        
        // ストリーミングが完了したらストリーミングフラグを解除
        if (is_streaming === false) {
            isProcessing = false;
            loadingIndicator.style.display = 'none';
            messageElement.classList.remove('streaming');
            
            // 最終レスポンスでは、既存の思考過程パネルがあれば更新
            if (thoughts && thoughts.length > 0 && !is_user) {
                addThoughtPanel(messageElement, thoughts, message, messageId, false);
            }
        }
    }
    
    // メッセージ要素の作成
    function createMessageElement(content, isUser, id) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
        messageDiv.id = id;
        
        // アバター部分
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        
        if (isUser) {
            avatarDiv.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"></path></svg>';
        } else {
            avatarDiv.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M19.39 10.74l-4.11-4.11c-.35-.35-.92-.35-1.27 0l-1.36 1.36c-.35.35-.35.92 0 1.27l4.11 4.11c.35.35.92.35 1.27 0l1.36-1.36c.35-.35.35-.92 0-1.27zM5.61 19.39l4.11-4.11c.35-.35.35-.92 0-1.27l-1.36-1.36c-.35-.35-.92-.35-1.27 0l-4.11 4.11c-.35.35-.35.92 0 1.27l1.36 1.36c.35.35.92.35 1.27 0z"/><path d="M13.23 14.88l-3.53-3.53c-.15-.15-.15-.39 0-.54l1.06-1.06c.15-.15.39-.15.54 0l3.53 3.53c.15.15.15.39 0 .54l-1.06 1.06c-.15.15-.39.15-.54 0z"/></svg>';
        }
        
        // コンテンツ部分
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = marked.parse(content);
        
        // 要素を組み立て
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        // ストリーミング中の場合はクラスを追加
        if (!isUser) {
            messageDiv.classList.add('streaming');
        }
        
        return messageDiv;
    }
    
    // 熟考過程パネルの追加
    function addDeliberationPanel(messageElement, deliberations, messageId) {
        // 既存のパネルがあれば削除
        const existingPanel = messageElement.nextElementSibling;
        if (existingPanel && existingPanel.classList.contains('deliberation-container')) {
            existingPanel.remove();
        }
        
        // 熟考過程パネルコンテナ
        const container = document.createElement('div');
        container.className = 'deliberation-container';
        container.setAttribute('data-message-id', messageId);
        
        // トグルボタン
        const toggleButton = document.createElement('button');
        toggleButton.className = 'deliberation-toggle';
        toggleButton.textContent = '🧠 熟考過程を見る';
        toggleButton.onclick = function() {
            const panel = this.nextElementSibling;
            panel.classList.toggle('active');
            this.textContent = panel.classList.contains('active') ? '🧠 熟考過程を隠す' : '🧠 熟考過程を見る';
        };
        
        // パネル本体
        const panel = document.createElement('div');
        panel.className = 'deliberation-panel';
        
        // 熟考ステップの追加
        deliberations.forEach((step, index) => {
            const stepElement = document.createElement('div');
            stepElement.className = 'deliberation-step';
            stepElement.textContent = `Step ${index + 1}: ${step}`;
            panel.appendChild(stepElement);
        });
        
        // 要素を組み立て
        container.appendChild(toggleButton);
        container.appendChild(panel);
        
        // メッセージ要素の後に挿入
        if (messageElement.nextSibling) {
            chatMessages.insertBefore(container, messageElement.nextSibling);
        } else {
            chatMessages.appendChild(container);
        }
    }
    
    // 熟考過程パネルの更新
    function updateDeliberationPanel(messageId, deliberations) {
        const container = document.querySelector(`.deliberation-container[data-message-id="${messageId}"]`);
        if (!container) {
            const messageElement = document.getElementById(messageId);
            if (messageElement) {
                addDeliberationPanel(messageElement, deliberations, messageId);
            }
            return;
        }
        
        const panel = container.querySelector('.deliberation-panel');
        panel.innerHTML = '';
        
        // 熟考ステップの追加
        deliberations.forEach((step, index) => {
            const stepElement = document.createElement('div');
            stepElement.className = 'deliberation-step';
            stepElement.textContent = `Step ${index + 1}: ${step}`;
            panel.appendChild(stepElement);
        });
    }
    
    // 思考過程パネルの追加
    function addThoughtPanel(messageElement, thoughts, finalMessage, messageId, isStreaming = false) {
        // 既存のパネルがあれば削除
        const existingPanel = messageElement.querySelector('.thought-container');
        if (existingPanel) {
            existingPanel.remove();
        }
        
        // メッセージコンテナを取得
        const contentContainer = messageElement.querySelector('.message-content');
        
        // 思考過程コンテナ
        const thoughtContainer = document.createElement('div');
        thoughtContainer.className = `thought-container ${isStreaming ? 'active' : ''}`;
        thoughtContainer.setAttribute('data-message-id', messageId);
        
        // 思考過程ヘッダー
        const thoughtHeader = document.createElement('div');
        thoughtHeader.className = 'thought-header';
        thoughtHeader.textContent = 'Thought:';
        thoughtContainer.appendChild(thoughtHeader);
        
        // 思考過程コンテンツ
        const thoughtContent = document.createElement('div');
        thoughtContent.className = 'thought-content';
        
        // 思考内容を結合
        thoughtContent.textContent = thoughts.join('\n');
        thoughtContainer.appendChild(thoughtContent);
        
        // 区切り線
        const divider = document.createElement('div');
        divider.className = 'thought-divider';
        thoughtContainer.appendChild(divider);
        
        // 最終メッセージ（既にcontentContainerに含まれているのでここでは追加しない）
        
        // 思考過程コンテナを追加
        contentContainer.appendChild(thoughtContainer);
        
        // ストリーミングが終了したらトグルボタンを追加
        if (!isStreaming) {
            // 既存のボタンがあれば削除
            const existingButtonContainer = messageElement.parentNode.querySelector('.thought-button-container');
            if (existingButtonContainer) {
                existingButtonContainer.remove();
            }
            
            // ボタンコンテナ
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'thought-button-container';
            buttonContainer.style.marginLeft = '60px';
            buttonContainer.style.marginTop = '8px';
            
            // トグルボタン
            const toggleButton = document.createElement('button');
            toggleButton.className = 'deliberation-toggle';
            toggleButton.textContent = '🧠 思考過程を見る';
            toggleButton.onclick = function() {
                const container = messageElement.querySelector('.thought-container');
                if (container) {
                    container.classList.toggle('active');
                    this.textContent = container.classList.contains('active') ? '🧠 思考過程を隠す' : '🧠 思考過程を見る';
                }
            };
            
            // ボタンを追加
            buttonContainer.appendChild(toggleButton);
            
            // メッセージの後にボタンを挿入
            if (messageElement.nextSibling) {
                messageElement.parentNode.insertBefore(buttonContainer, messageElement.nextSibling);
            } else {
                messageElement.parentNode.appendChild(buttonContainer);
            }
            
            // 初期状態では非表示
            thoughtContainer.classList.remove('active');
        }
    }
    
    // 思考過程パネルの更新
    function updateThoughtPanel(messageId, thoughts, finalMessage) {
        // メッセージ要素を取得
        const messageElement = document.getElementById(messageId);
        if (!messageElement) return;
        
        // 思考過程コンテナを取得
        let thoughtContainer = messageElement.querySelector('.thought-container');
        
        // 思考過程コンテナがない場合は新規作成
        if (!thoughtContainer) {
            addThoughtPanel(messageElement, thoughts, finalMessage, messageId, true);
            return;
        }
        
        // 思考過程コンテンツを更新
        const thoughtContent = thoughtContainer.querySelector('.thought-content');
        if (thoughtContent) {
            thoughtContent.textContent = thoughts.join('\n');
        }
    }
    
    // 下にスクロール
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // メッセージの送信
    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message || isProcessing) return;
        
        // ユーザーメッセージの表示
        const messageElement = createMessageElement(message, true, `user-${Date.now()}`);
        chatMessages.appendChild(messageElement);
        scrollToBottom();
        
        // APIリクエストの送信
        isProcessing = true;
        loadingIndicator.style.display = 'flex';
        
        if (webSocket && webSocket.readyState === WebSocket.OPEN) {
            // WebSocketで送信
            webSocket.send(JSON.stringify({
                message: message,
                resume: chatMessages.children.length > 1 // メッセージが既に存在する場合はresume=true
            }));
        } else {
            // フォールバック: REST APIを使用
            fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    resume: chatMessages.children.length > 1
                })
            })
            .then(response => response.json())
            .then(data => {
                handleIncomingMessage({
                    ...data,
                    is_streaming: false,
                    thoughts: data.thoughts || [] // thoughtsを明示的に取り出す
                });
            })
            .catch(error => {
                console.error('Error:', error);
                isProcessing = false;
                loadingIndicator.style.display = 'none';
                
                // エラーメッセージの表示
                const errorElement = createMessageElement('メッセージの送信中にエラーが発生しました。もう一度お試しください。', false, `error-${Date.now()}`);
                chatMessages.appendChild(errorElement);
                scrollToBottom();
            });
        }
        
        // 入力フィールドのクリア
        messageInput.value = '';
    }
    
    // 送信ボタンのクリックイベント
    sendButton.addEventListener('click', sendMessage);
    
    // Enterキーでの送信（Shift+Enterは改行）
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // 入力フィールドの高さ自動調整
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = (messageInput.scrollHeight) + 'px';
    });
    
    // WebSocket接続の初期化
    initWebSocket();
});
