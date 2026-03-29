document.addEventListener("DOMContentLoaded", function () {
    const questionModal = document.getElementById("questionModal");
    const nextStepModal = document.getElementById("nextStepModal");
    const presetQuestionForm = document.getElementById("presetQuestionForm");
    const presetQuestionInput = document.getElementById("presetQuestionInput");
    const customQuestionBox = document.getElementById("customQuestionBox");
    const chatHistory = document.getElementById("chatHistory");
    const exitForm = document.getElementById("exitForm");

    const openQuestionModalBtn = document.getElementById("openQuestionModalBtn");
    const showCustomBoxBtn = document.getElementById("showCustomBoxBtn");
    const hideCustomBoxBtn = document.getElementById("hideCustomBoxBtn");
    const openCustomFromModalBtn = document.getElementById("openCustomFromModalBtn");
    const modalExitBtn = document.getElementById("modalExitBtn");
    const askAnotherBtn = document.getElementById("askAnotherBtn");
    const askCustomAfterAnswerBtn = document.getElementById("askCustomAfterAnswerBtn");
    const nextStepExitBtn = document.getElementById("nextStepExitBtn");

    const presetButtons = document.querySelectorAll(".preset-question-btn");
    const showNextStep = window.CHAT_PAGE_STATE && window.CHAT_PAGE_STATE.showNextStep === 1;

    function openModal(modal) {
        if (modal) {
            modal.classList.add("show");
        }
    }

    function closeModal(modal) {
        if (modal) {
            modal.classList.remove("show");
        }
    }

    function showCustomQuestionBox() {
        closeModal(questionModal);
        closeModal(nextStepModal);

        if (customQuestionBox) {
            customQuestionBox.classList.add("active");
            const textarea = customQuestionBox.querySelector("textarea");
            if (textarea) {
                textarea.focus();
            }
        }
    }

    function hideCustomQuestionBox() {
        if (customQuestionBox) {
            customQuestionBox.classList.remove("active");
        }
    }

    function submitPresetQuestion(questionText) {
        if (!presetQuestionInput || !presetQuestionForm) return;
        presetQuestionInput.value = questionText;
        presetQuestionForm.submit();
    }

    function exitChat() {
        if (exitForm) {
            exitForm.requestSubmit();
        }
    }

    if (chatHistory) {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    if (presetButtons.length > 0) {
        presetButtons.forEach((btn) => {
            btn.addEventListener("click", function () {
                const question = btn.getAttribute("data-question") || "";
                submitPresetQuestion(question);
            });
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

    if (showNextStep) {
        openModal(nextStepModal);
    } else {
        openModal(questionModal);
    }

    [questionModal, nextStepModal].forEach((modal) => {
        if (!modal) return;

        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                closeModal(modal);
            }
        });
    });
});
