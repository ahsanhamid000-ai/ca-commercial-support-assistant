document.addEventListener("DOMContentLoaded", function () {
    const state = window.CHAT_PAGE_STATE || {};
    const askUrl = state.askUrl || "";
    const homeUrl = state.homeUrl || "/";

    const questionModal = document.getElementById("questionModal");
    const nextStepModal = document.getElementById("nextStepModal");
    const customQuestionBox = document.getElementById("customQuestionBox");
    const chatHistory = document.getElementById("chatHistory");
    const statusText = document.getElementById("statusText");

    const openQuestionModalBtn = document.getElementById("openQuestionModalBtn");
    const showCustomBoxBtn = document.getElementById("showCustomBoxBtn");
    const hideCustomBoxBtn = document.getElementById("hideCustomBoxBtn");
    const openCustomFromModalBtn = document.getElementById("openCustomFromModalBtn");
    const modalExitBtn = document.getElementById("modalExitBtn");
    const exitBtn = document.getElementById("exitBtn");
    const askAnotherBtn = document.getElementById("askAnotherBtn");
    const askCustomAfterAnswerBtn = document.getElementById("askCustomAfterAnswerBtn");
    const nextStepExitBtn = document.getElementById("nextStepExitBtn");
    const submitCustomQuestionBtn = document.getElementById("submitCustomQuestionBtn");

    const questionInput = document.getElementById("questionInput");
    const fallbackMode = document.getElementById("fallbackMode");
    const presetButtons = document.querySelectorAll(".preset-question-btn");

    function openModal(modal) {
        if (modal) modal.classList.add("show");
    }

    function closeModal(modal) {
        if (modal) modal.classList.remove("show");
    }

    function showStatus(message) {
        if (!statusText) return;
        statusText.textContent = message;
        statusText.classList.add("show");
    }

    function hideStatus() {
        if (!statusText) return;
        statusText.classList.remove("show");
    }

    function showCustomQuestionBox() {
        closeModal(questionModal);
        closeModal(nextStepModal);

        if (customQuestionBox) {
            customQuestionBox.classList.add("active");
        }

        if (questionInput) {
            questionInput.focus();
        }
    }

    function hideCustomQuestionBox() {
        if (customQuestionBox) {
            customQuestionBox.classList.remove("active");
        }

        if (questionInput) {
            questionInput.value = "";
        }
    }

    function exitChat() {
        window.location.href = homeUrl;
    }

    function scrollHistoryToBottom() {
        if (chatHistory) {
            chatHistory.scrollTop = chatHistory.scrollHeight;
        }
    }

    function createMessageBubble(role, text, source = "") {
        const wrapper = document.createElement("div");
        wrapper.className = `message ${role}`;

        const meta = document.createElement("div");
        meta.className = "message-meta";

        const label = document.createElement("strong");
        label.textContent = role === "user" ? "You:" : "Assistant:";
        meta.appendChild(label);

        if (role === "assistant" && source) {
            const badge = document.createElement("span");
            badge.className = "source-badge";
            badge.textContent = source;
            meta.appendChild(badge);
        }

        const body = document.createElement("div");
        body.textContent = text;

        wrapper.appendChild(meta);
        wrapper.appendChild(body);

        return wrapper;
    }

    function appendConversation(question, answer, source = "") {
        if (!chatHistory) return;

        const initialPlaceholder = chatHistory.querySelector(".message.assistant");
        if (initialPlaceholder && chatHistory.children.length === 1) {
            const content = initialPlaceholder.textContent || "";
            if (content.includes("Please choose a question from the popup list")) {
                chatHistory.innerHTML = "";
            }
        }

        chatHistory.appendChild(createMessageBubble("user", question));
        chatHistory.appendChild(createMessageBubble("assistant", answer, source));
        scrollHistoryToBottom();
    }

    function setButtonsDisabled(disabled) {
        const allButtons = document.querySelectorAll("button");
        allButtons.forEach((button) => {
            button.disabled = disabled;
        });
    }

    async function askQuestion(question, questionMode, selectedFallbackMode) {
        if (!askUrl) {
            appendConversation(
                question,
                "The chatbot endpoint is not configured correctly.",
                ""
            );
            return;
        }

        showStatus("Processing your question...");
        setButtonsDisabled(true);

        try {
            const formData = new FormData();
            formData.append("question", question);
            formData.append("question_mode", questionMode);
            formData.append("fallback_mode", selectedFallbackMode || "document_then_openai");

            const response = await fetch(askUrl, {
                method: "POST",
                body: formData,
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                const errorMessage = data.message || "The chatbot could not answer right now.";
                appendConversation(question, errorMessage, "");
                closeModal(questionModal);
                closeModal(nextStepModal);
                return;
            }

            appendConversation(
                data.question || question,
                data.answer || "No answer returned.",
                data.source || ""
            );

            hideCustomQuestionBox();
            closeModal(questionModal);
            openModal(nextStepModal);
        } catch (error) {
            appendConversation(question, "A network or server error occurred. Please try again.", "");
            closeModal(questionModal);
            closeModal(nextStepModal);
        } finally {
            hideStatus();
            setButtonsDisabled(false);
        }
    }

    if (chatHistory) {
        scrollHistoryToBottom();
    }

    if (presetButtons.length > 0) {
        presetButtons.forEach((btn) => {
            btn.addEventListener("click", function () {
                const question = btn.getAttribute("data-question") || "";
                if (question.trim()) {
                    askQuestion(question, "preset", "document_only");
                }
            });
        });
    }

    if (submitCustomQuestionBtn) {
        submitCustomQuestionBtn.addEventListener("click", function () {
            const question = (questionInput && questionInput.value ? questionInput.value : "").trim();
            const mode = fallbackMode ? fallbackMode.value : "document_then_openai";

            if (!question) {
                showStatus("Please type a custom question first.");
                setTimeout(hideStatus, 1800);
                return;
            }

            askQuestion(question, "custom", mode);
        });
    }

    if (openQuestionModalBtn) {
        openQuestionModalBtn.addEventListener("click", function () {
            hideCustomQuestionBox();
            closeModal(nextStepModal);
            openModal(questionModal);
        });
    }

    if (showCustomBoxBtn) {
        showCustomBoxBtn.addEventListener("click", function () {
            showCustomQuestionBox();
        });
    }

    if (hideCustomBoxBtn) {
        hideCustomBoxBtn.addEventListener("click", function () {
            hideCustomQuestionBox();
        });
    }

    if (openCustomFromModalBtn) {
        openCustomFromModalBtn.addEventListener("click", function () {
            showCustomQuestionBox();
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
            closeModal(nextStepModal);
            hideCustomQuestionBox();
            openModal(questionModal);
        });
    }

    if (askCustomAfterAnswerBtn) {
        askCustomAfterAnswerBtn.addEventListener("click", function () {
            showCustomQuestionBox();
        });
    }

    if (nextStepExitBtn) {
        nextStepExitBtn.addEventListener("click", function () {
            exitChat();
        });
    }

    [questionModal, nextStepModal].forEach((modal) => {
        if (!modal) return;

        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                closeModal(modal);
            }
        });
    });

    if (questionInput) {
        questionInput.addEventListener("keydown", function (event) {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                event.preventDefault();
                if (submitCustomQuestionBtn) {
                    submitCustomQuestionBtn.click();
                }
            }
        });
    }

    openModal(questionModal);
});
