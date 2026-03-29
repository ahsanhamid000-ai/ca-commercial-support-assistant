if (!window.__caChatWidgetInitialized) {
    window.__caChatWidgetInitialized = true;

    document.addEventListener("DOMContentLoaded", function () {
        const state = window.CHAT_PAGE_STATE || {};
        const askUrl = state.askUrl || "";
        const homeUrl = state.homeUrl || "/";
        const notFoundMessage =
            state.notFoundMessage || "The requested information was not found in the uploaded document.";
        const aiFallbackEnabled = !!state.aiFallbackEnabled;

        const chatBody = document.getElementById("chatBody");
        const messageInput = document.getElementById("messageInput");
        const sendBtn = document.getElementById("sendBtn");
        const typingStatus = document.getElementById("typingStatus");
        const quickActions = document.getElementById("quickActions");
        const useAiBtn = document.getElementById("useAiBtn");

        const promptModal = document.getElementById("promptModal");
        const openPromptBtn = document.getElementById("openPromptBtn");
        const openPromptFromInputBtn = document.getElementById("openPromptFromInputBtn");
        const closePromptModalBtn = document.getElementById("closePromptModalBtn");
        const modalExitBtn = document.getElementById("modalExitBtn");
        const exitBtn = document.getElementById("exitBtn");
        const askAnotherBtn = document.getElementById("askAnotherBtn");

        const presetButtons = document.querySelectorAll(".preset-question-btn");

        let requestInFlight = false;
        let lastSubmittedQuestion = "";
        let lastSubmittedAt = 0;
        let lastNotFoundQuestion = "";

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

        function showUseAiButton(show) {
            if (!useAiBtn) return;
            if (!aiFallbackEnabled) {
                useAiBtn.classList.remove("show");
                return;
            }
            useAiBtn.classList.toggle("show", !!show);
        }

        function clearAiFallbackState() {
            lastNotFoundQuestion = "";
            showUseAiButton(false);
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

        function isDuplicateSubmission(question) {
            const now = Date.now();
            const sameQuestion = question === lastSubmittedQuestion;
            const tooSoon = now - lastSubmittedAt < 1500;
            return sameQuestion && tooSoon;
        }

        function markSubmission(question) {
            lastSubmittedQuestion = question;
            lastSubmittedAt = Date.now();
        }

        async function parseJsonSafely(response) {
            const text = await response.text();
            try {
                return JSON.parse(text);
            } catch (error) {
                return {
                    success: false,
                    message: "The server returned an invalid response."
                };
            }
        }

        async function askQuestion(question, options = {}) {
            const trimmed = (question || "").trim();
            const mode = options.mode === "ai" ? "ai" : "document";
            const echoUser = options.echoUser !== false;

            if (!trimmed) return;
            if (requestInFlight) return;
            if (mode === "document" && isDuplicateSubmission(trimmed)) return;

            requestInFlight = true;

            if (mode === "document") {
                markSubmission(trimmed);
                clearAiFallbackState();
            }

            if (!askUrl) {
                appendMessage("assistant", "The chatbot endpoint is not configured correctly.");
                requestInFlight = false;
                return;
            }

            if (echoUser) {
                appendMessage("user", trimmed);
            }

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
                formData.append("mode", mode);

                const response = await fetch(askUrl, {
                    method: "POST",
                    body: formData,
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });

                const data = await parseJsonSafely(response);

                if (!response.ok || !data.success) {
                    appendMessage("assistant", data.message || "The chatbot could not answer right now.");
                    clearAiFallbackState();
                    return;
                }

                const answerText = data.answer || "No answer returned.";
                appendMessage("assistant", answerText);

                const isNotFound =
                    mode === "document" &&
                    (data.not_found === true || answerText.trim() === notFoundMessage);

                if (isNotFound && aiFallbackEnabled && data.ai_fallback_available) {
                    lastNotFoundQuestion = trimmed;
                    showUseAiButton(true);
                } else {
                    clearAiFallbackState();
                }

                showQuickActions(true);
            } catch (error) {
                appendMessage("assistant", "A network or server error occurred. Please try again.");
                clearAiFallbackState();
            } finally {
                showTyping(false);
                setBusy(false);
                requestInFlight = false;
            }
        }

        presetButtons.forEach((btn) => {
            if (btn.dataset.bound === "1") return;
            btn.dataset.bound = "1";

            btn.addEventListener("click", function (event) {
                event.preventDefault();
                event.stopPropagation();
                const question = btn.getAttribute("data-question") || "";
                askQuestion(question, { mode: "document", echoUser: true });
            });
        });

        if (sendBtn && sendBtn.dataset.bound !== "1") {
            sendBtn.dataset.bound = "1";
            sendBtn.addEventListener("click", function (event) {
                event.preventDefault();
                askQuestion(messageInput ? messageInput.value : "", { mode: "document", echoUser: true });
            });
        }

        if (messageInput && messageInput.dataset.bound !== "1") {
            messageInput.dataset.bound = "1";
            messageInput.addEventListener("keydown", function (event) {
                if (event.key === "Enter") {
                    event.preventDefault();
                    askQuestion(messageInput.value, { mode: "document", echoUser: true });
                }
            });
        }

        if (useAiBtn && useAiBtn.dataset.bound !== "1") {
            useAiBtn.dataset.bound = "1";
            useAiBtn.addEventListener("click", function () {
                if (!lastNotFoundQuestion) return;
                askQuestion(lastNotFoundQuestion, { mode: "ai", echoUser: false });
            });
        }

        if (openPromptBtn && openPromptBtn.dataset.bound !== "1") {
            openPromptBtn.dataset.bound = "1";
            openPromptBtn.addEventListener("click", function () {
                openModal(promptModal);
            });
        }

        if (openPromptFromInputBtn && openPromptFromInputBtn.dataset.bound !== "1") {
            openPromptFromInputBtn.dataset.bound = "1";
            openPromptFromInputBtn.addEventListener("click", function () {
                openModal(promptModal);
            });
        }

        if (closePromptModalBtn && closePromptModalBtn.dataset.bound !== "1") {
            closePromptModalBtn.dataset.bound = "1";
            closePromptModalBtn.addEventListener("click", function () {
                closeModal(promptModal);
            });
        }

        if (modalExitBtn && modalExitBtn.dataset.bound !== "1") {
            modalExitBtn.dataset.bound = "1";
            modalExitBtn.addEventListener("click", function () {
                exitChat();
            });
        }

        if (exitBtn && exitBtn.dataset.bound !== "1") {
            exitBtn.dataset.bound = "1";
            exitBtn.addEventListener("click", function () {
                exitChat();
            });
        }

        if (askAnotherBtn && askAnotherBtn.dataset.bound !== "1") {
            askAnotherBtn.dataset.bound = "1";
            askAnotherBtn.addEventListener("click", function () {
                openModal(promptModal);
            });
        }

        if (promptModal && promptModal.dataset.bound !== "1") {
            promptModal.dataset.bound = "1";
            promptModal.addEventListener("click", function (event) {
                if (event.target === promptModal) {
                    closeModal(promptModal);
                }
            });
        }

        scrollToBottom();
        openModal(promptModal);
    });
}
