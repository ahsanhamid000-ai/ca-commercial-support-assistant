document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    if (!chatForm) return;

    chatForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const formData = new FormData(chatForm);
        const question = formData.get("question");
        const chatHistory = document.getElementById("chat-history");

        if (!question || !question.trim()) {
            return;
        }

        const response = await fetch(chatForm.action, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        const userDiv = document.createElement("div");
        userDiv.className = "chat-message user";
        userDiv.innerHTML = `<strong>You:</strong> ${question}`;
        chatHistory.appendChild(userDiv);

        const assistantDiv = document.createElement("div");
        assistantDiv.className = "chat-message assistant";
        assistantDiv.innerHTML = `<strong>Assistant:</strong> ${data.message || data.answer}`;
        chatHistory.appendChild(assistantDiv);

        chatForm.reset();
        chatHistory.scrollTop = chatHistory.scrollHeight;
    });
});
