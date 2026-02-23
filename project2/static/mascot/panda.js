// static/mascot/panda.js
(function () {
    const mascot = document.getElementById("panda-mascot");
    const chatContainer = document.getElementById("chat-container");
    if (!mascot || !chatContainer) return;

    const wrap = mascot.querySelector(".panda-wrap");
    const bubble = mascot.querySelector(".panda-bubble");
    const userInput = document.getElementById("user-input");
    const resizer = chatContainer.querySelector(".chat-resizer");
    const chatBody = document.getElementById("chat-body");
    const sendBtn = document.getElementById("send-btn");

    const config = {
        bubbleMs: 2800,
        edgePadding: 18,
        mascotKey: "panda:mascot:pos",
        chatKey: "panda:chat:pos",
        sizeKey: "panda:chat:size", 
        minW: 320,
        minH: 400
    };

    let draggingMascot = false;
    let draggingChat = false;
    let resizingChat = false;
    let isChatOpen = false;
    let moving = false;

    // --- SHARED UTILS ---
    const clamp = (n, min, max) => Math.max(min, Math.min(max, n));

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function setMode(mode) {
        mascot.classList.remove("idle", "moving", "celebrate");
        if (mode) mascot.classList.add(mode);
    }

    // --- CONFETTI ENGINE ---
    function launchConfetti() {
        const container = document.getElementById("panda-confetti");
        if (!container) return;
        const colors = ['#6c5ce7', '#a29bfe', '#ffeaa7', '#55efc4', '#fab1a0'];
        for (let i = 0; i < 50; i++) {
            const piece = document.createElement("div");
            piece.className = "panda-confetti-piece";
            piece.style.left = Math.random() * 100 + "vw";
            piece.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            piece.style.transform = `rotate(${Math.random() * 360}deg)`;
            piece.style.animationDuration = (Math.random() * 2 + 1) + "s";
            piece.style.animationDelay = Math.random() * 0.5 + "s";
            container.appendChild(piece);
            setTimeout(() => piece.remove(), 3000);
        }
    }

    // --- CHAT WINDOW LOGIC ---
    window.PandaAgent = {
        hasGreeted: false,

        toggleChat(forceState) {
            isChatOpen = forceState !== undefined ? forceState : !isChatOpen;
            if (isChatOpen) {
                chatContainer.style.display = 'flex';
                if (bubble) bubble.classList.remove("show");
                if (userInput) userInput.focus();
                setMode(null);
                if (!this.hasGreeted) {
                    this.fetchGreeting();
                    this.hasGreeted = true;
                }
            } else {
                chatContainer.style.display = 'none';
                setMode("idle");
            }
        },

        // UPDATED: Now supports rebuilding history from Django Session
        fetchGreeting() {
            fetch('/chatbot/greet/')
                .then(response => response.json())
                .then(data => {
                    if (data.history && data.history.length > 0) {
                        // Clear current view and rebuild from session memory
                        if (chatBody) chatBody.innerHTML = ''; 
                        data.history.forEach(msg => {
                            this.appendMessage(msg.sender, msg.text);
                        });
                    } else if (data.greeting) {
                        this.appendMessage('panda', data.greeting);
                    }
                })
                .catch(err => console.error("Greeting/History Error:", err));
        },

        appendMessage(sender, text) {
            if (!chatBody) return;
            const msgDiv = document.createElement("div");
            msgDiv.className = `chat-message ${sender}-message`;
            
            if (sender === 'panda' && typeof marked !== 'undefined') {
                msgDiv.innerHTML = marked.parse(text);
            } else {
                msgDiv.textContent = text;
            }
            
            chatBody.appendChild(msgDiv);
            chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: 'smooth' });
        },

        async sendMessage() {
            const text = userInput.value.trim();
            if (!text) return;

            this.appendMessage('user', text);
            userInput.value = '';
            this.showThinking();

            try {
                const response = await fetch('/chatbot/ask/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: `message=${encodeURIComponent(text)}`
                });

                const data = await response.json();
                this.hideBubble();

                if (data.response) {
                    this.appendMessage('panda', data.response);
                    
                    const successTerms = ["success", "posted", "sent", "created", "updated", "live"];
                    if (successTerms.some(term => data.response.toLowerCase().includes(term))) {
                        setMode("celebrate");
                        launchConfetti();
                        setTimeout(() => setMode("idle"), 3000);
                    }
                }
            } catch (error) {
                this.hideBubble();
                this.appendMessage('panda', "I'm having trouble reaching the database right now.");
            }
        },

        showThinking() {
            if (bubble) {
                bubble.innerHTML = `<div class="panda-thinking"><span></span><span></span><span></span></div>`;
                bubble.classList.add("show");
            }
        },

        hideBubble() {
            if (bubble) bubble.classList.remove("show");
        }
    };

    // --- DRAGGING MASCOT ---
    function initMascotDraggable() {
        let dragOffset = { x: 0, y: 0 };
        wrap.addEventListener("pointerdown", (e) => {
            if (moving) return;
            draggingMascot = true;
            mascot.classList.add("dragging");
            const rect = mascot.getBoundingClientRect();
            dragOffset.x = e.clientX - rect.left;
            dragOffset.y = e.clientY - rect.top;
            mascot.style.transition = "none";
            wrap.setPointerCapture(e.pointerId);
        });
        window.addEventListener("pointermove", (e) => {
            if (!draggingMascot) return;
            const x = clamp(e.clientX - dragOffset.x, config.edgePadding, window.innerWidth - 80);
            const y = clamp(e.clientY - dragOffset.y, config.edgePadding, window.innerHeight - 80);
            mascot.style.left = `${x}px`; mascot.style.top = `${y}px`;
            mascot.style.bottom = "auto"; mascot.style.right = "auto";
        });
        window.addEventListener("pointerup", () => {
            if (!draggingMascot) return;
            draggingMascot = false;
            mascot.classList.remove("dragging");
            setMode("idle");
            localStorage.setItem(config.mascotKey, JSON.stringify({ x: mascot.style.left, y: mascot.style.top }));
        });
    }

    // --- DRAGGING & RESIZING CHAT WINDOW ---
    function initChatControls() {
        let chatOffset = { x: 0, y: 0 };
        const header = chatContainer.querySelector(".chat-header");

        header.addEventListener("pointerdown", (e) => {
            if (e.target.closest('button') || e.target.closest('input')) return;
            draggingChat = true;
            const rect = chatContainer.getBoundingClientRect();
            chatOffset.x = e.clientX - rect.left;
            chatOffset.y = e.clientY - rect.top;
            chatContainer.style.transition = "none";
            header.setPointerCapture(e.pointerId);
        });

        if (resizer) {
            resizer.addEventListener("pointerdown", (e) => {
                e.preventDefault();
                e.stopPropagation(); 
                resizingChat = true;
                resizer.setPointerCapture(e.pointerId);
            });
        }

        window.addEventListener("pointermove", (e) => {
            if (draggingChat) {
                const x = clamp(e.clientX - chatOffset.x, 0, window.innerWidth - chatContainer.offsetWidth);
                const y = clamp(e.clientY - chatOffset.y, 0, window.innerHeight - chatContainer.offsetHeight);
                chatContainer.style.left = `${x}px`; chatContainer.style.top = `${y}px`;
                chatContainer.style.bottom = "auto"; chatContainer.style.right = "auto";
            } 
            if (resizingChat) {
                const rect = chatContainer.getBoundingClientRect();
                const newW = clamp(e.clientX - rect.left, config.minW, window.innerWidth - rect.left - 20);
                const newH = clamp(e.clientY - rect.top, config.minH, window.innerHeight - rect.top - 20);
                chatContainer.style.width = newW + "px";
                chatContainer.style.height = newH + "px";
            }
        });

        window.addEventListener("pointerup", () => {
            if (draggingChat) {
                draggingChat = false;
                localStorage.setItem(config.chatKey, JSON.stringify({ x: chatContainer.style.left, y: chatContainer.style.top }));
            }
            if (resizingChat) {
                resizingChat = false;
                localStorage.setItem(config.sizeKey, JSON.stringify({ w: chatContainer.style.width, h: chatContainer.style.height }));
            }
        });
    }

    function loadPersistedState() {
        const mPos = JSON.parse(localStorage.getItem(config.mascotKey));
        const cPos = JSON.parse(localStorage.getItem(config.chatKey));
        const cSize = JSON.parse(localStorage.getItem(config.sizeKey));
        if (mPos) { mascot.style.left = mPos.x; mascot.style.top = mPos.y; mascot.style.right = "auto"; mascot.style.bottom = "auto"; }
        if (cPos) { chatContainer.style.left = cPos.x; chatContainer.style.top = cPos.y; chatContainer.style.right = "auto"; chatContainer.style.bottom = "auto"; }
        if (cSize) { chatContainer.style.width = cSize.w; chatContainer.style.height = cSize.h; }
    }

    wrap.addEventListener("click", () => { if (!draggingMascot) window.PandaAgent.toggleChat(); });
    if (sendBtn) sendBtn.addEventListener("click", () => window.PandaAgent.sendMessage());
    if (userInput) userInput.addEventListener("keypress", (e) => { if (e.key === "Enter") window.PandaAgent.sendMessage(); });

    mascot.classList.add("idle", "blink");
    initMascotDraggable();
    initChatControls();
    loadPersistedState();

    window.addEventListener("resize", () => {
        const mRect = mascot.getBoundingClientRect();
        mascot.style.left = clamp(mRect.left, 0, window.innerWidth - 80) + "px";
        mascot.style.top = clamp(mRect.top, 0, window.innerHeight - 80) + "px";
    });
})();