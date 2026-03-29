document.addEventListener("DOMContentLoaded", function () {
    const state = window.CHAT_PAGE_STATE || {};
    const askUrl = state.askUrl || "";
    const homeUrl = state.homeUrl || "/";

    const chatBody = document.getElementById("chatBody");
    const messageInput = document.getElementById("messageInput");
    const sendBtn = document.getElementById("sendBtn");
    const typingStatus = document.getElementById("typingStatus");
    const quickActions = document.getElementById("quickActions");

    const promptModal = document.getElementById("promptModal");
    const openPromptBtn = document.getElementById("openPromptBtn");
    const openPromptFromInputBtn = document.getElementById("openPromptFromInputBtn");
    const closePromptModalBtn = document.getElementById("closePromptModalBtn");
    const modalExitBtn = document.getElementById("modalExitBtn");
    const exitBtn = document.getElementById("exitBtn");
    const askAnotherBtn = document.getElementById("askAnotherBtn");

    const presetButtons = document.querySelectorAll(".preset-question-btn");

    let requestInFlight = false;

    function scrollToBottom() {
        if (chatBody) {
            chatBody.scrollTop = chatBody.scrollHeight;
        }
    }

    function openModal(modal) {
        if (modal) modal.classList.add("show");
    }

    function closeModal(modal) {
        if (modal) modal.classList.remove("show");
    }

    function showTyping(show) {
        if (!typingStatus) return;
        typingStatus.classList.toggle("show", !!show);
    }

    function showQuickActions(show) {
        if (!quickActions) return;
        quickActions.classList.toggle("show", !!show);
    }

    function createBubble(role, text) {
        const row = document.createElement("div");
        row.className = `bubble-row ${role}`;

        const bubble = document.createElement("div");
        bubble.className = `bubble ${role}`;

        const label = document.createElement("div");
        label.className = "bubble-label";
        label.textContent = role === "user" ? "You" : "Assistant";

        const body = document.createElement("div");
        body.textContent = text;

        bubble.appendChild(label);
        bubble.appendChild(body);
        row.appendChild(bubble);

        return row;
    }

    function appendMessage(role, text) {
        if (!chatBody) return;

        const initial = document.getElementById("initialBotBubble");
        if (initial) {
            initial.remove();
        }

        chatBody.appendChild(createBubble(role, text));
        scrollToBottom();
    }

    function setBusy(isBusy) {
        const buttons = document.querySelectorAll("button");
        buttons.forEach((btn) => {
            btn.disabled = isBusy;
        });

        if (messageInput) {
            messageInput.disabled = isBusy;
        }
    }

    function exitChat() {
        window.location.href = homeUrl;
    }

    async function askQuestion(question) {
        const trimmed = (question || "").trim();
        if (!trimmed || requestInFlight) return;

        requestInFlight = true;

        if (!askUrl) {
            appendMessage("assistant", "The chatbot endpoint is not configured correctly.");
            requestInFlight = false;
            return;
        }

        appendMessage("user", trimmed);

        if (messageInput) {
            messageInput.value = "";
        }

        closeModal(promptModal);
        showQuickActions(false);
        showTyping(true);
        setBusy(true);

        try {
            const formData = new FormData();
            formData.append("question", trimmed);

            const response = await fetch(askUrl, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                appendMessage("assistant", data.message || "The chatbot could not answer right now.");
                return;
            }

            appendMessage("assistant", data.answer || "No answer returned.");
            showQuickActions(true);
        } catch (error) {
            appendMessage("assistant", "A network or server error occurred. Please try again.");
        } finally {
            showTyping(false);
            setBusy(false);
            requestInFlight = false;
        }
    }

    if (presetButtons.length > 0) {
        presetButtons.forEach((btn) => {
            btn.addEventListener("click", function () {
                if (requestInFlight) return;
                const question = btn.getAttribute("data-question") || "";
                askQuestion(question);
            });
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener("click", function () {
            askQuestion(messageInput ? messageInput.value : "");
        });
    }

    if (messageInput) {
        messageInput.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                askQuestion(messageInput.value);
            }
        });
    }

    if (openPromptBtn) {
        openPromptBtn.addEventListener("click", function () {
            openModal(promptModal);
        });
    }

    if (openPromptFromInputBtn) {
        openPromptFromInputBtn.addEventListener("click", function () {
            openModal(promptModal);
        });
    }

    if (closePromptModalBtn) {
        closePromptModalBtn.addEventListener("click", function () {
            closeModal(promptModal);
        });
    }

    if (modalExitBtn) {
        modalExitBtn.addEventListener("click", function () {
            exitChat();
        });
    }

    if (exitBtn) {
        exitBtn.addEventListener("click", function () {
            exitChat();
        });
    }

    if (askAnotherBtn) {
        askAnotherBtn.addEventListener("click", function () {
            openModal(promptModal);
        });
    }

    if (promptModal) {
        promptModal.addEventListener("click", function (event) {
            if (event.target === promptModal) {
                closeModal(promptModal);
            }
        });
    }

    scrollToBottom();
    openModal(promptModal);
});
