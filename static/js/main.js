document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    if (!chatForm) return;

    const chatHistory = document.getElementById("chat-history");
    const chatStatus = document.getElementById("chat-status");
    const sendButton = document.getElementById("send-button");
    const questionInput = document.getElementById("question");

    function appendMessage(role, text) {
        const wrapper = document.createElement("div");
        wrapper.className = `chat-message ${role}`;

        const strong = document.createElement("strong");
        strong.textContent = role === "user" ? "You:" : "Assistant:";

        wrapper.appendChild(strong);
        wrapper.appendChild(document.createTextNode(" " + text));
        chatHistory.appendChild(wrapper);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    chatForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const question = questionInput.value.trim();
        if (!question) return;

        const formData = new FormData(chatForm);

        sendButton.disabled = true;
        chatStatus.style.display = "block";

        appendMessage("user", question);

        try {
            const response = await fetch(chatForm.action, {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                appendMessage("assistant", data.message || "Something went wrong.");
            } else {
                appendMessage("assistant", data.answer);
            }

            questionInput.value = "";
        } catch (error) {
            appendMessage(
                "assistant",
                "The chatbot is temporarily unavailable. Please try again."
            );
        } finally {
            sendButton.disabled = false;
            chatStatus.style.display = "none";
            questionInput.focus();
        }
    });
});
