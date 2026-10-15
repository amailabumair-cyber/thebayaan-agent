document.addEventListener("DOMContentLoaded", () => {
    const consoleBox = document.getElementById("consoleBox");
    const cmdInput = document.getElementById("cmdInput");
    const btnSend = document.getElementById("btnSend");
    const queueContainer = document.getElementById("queueContainer");

    // فوری کمانڈ بٹنز کے کلک ایونٹس
    document.querySelectorAll(".btn-cmd").forEach(btn => {
        btn.addEventListener("click", () => {
            const cmd = btn.getAttribute("data-cmd");
            executeCommand(cmd);
        });
    });

    btnSend.addEventListener("click", () => {
        const text = cmdInput.value.trim();
        if (text) {
            executeCommand(text);
            cmdInput.value = "";
        }
    });

    cmdInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            const text = cmdInput.value.trim();
            if (text) {
                executeCommand(text);
                cmdInput.value = "";
            }
        }
    });

    async function executeCommand(cmdText) {
        appendConsole(`> ${cmdText}`, "command");
        try {
            const resp = await fetch("/api/command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ command: cmdText })
            });
            const data = await resp.json();
            if (data.message_urdu) {
                appendConsole(data.message_urdu, data.success ? "success" : "error");
            } else {
                appendConsole(JSON.stringify(data, null, 2), "info");
            }
            // اگر پوسٹس یا آڈٹ تبدیل ہوا ہو تو قطار ریفریش کریں
            if (cmdText.includes("پوسٹ") || cmdText.includes("آڈٹ") || cmdText.includes("کوئز") || cmdText.includes("پول")) {
                loadQueue();
            }
        } catch (err) {
            appendConsole(`نیٹ ورک خرابی: ${err.message}`, "error");
        }
    }

    function appendConsole(text, type = "normal") {
        const time = new Date().toLocaleTimeString('ur-PK', { hour: '2-digit', minute: '2-digit' });
        const line = document.createElement("div");
        line.style.marginBottom = "8px";
        line.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
        line.style.paddingBottom = "4px";

        if (type === "command") {
            line.style.color = "#ffb703";
            line.style.fontWeight = "bold";
        } else if (type === "success") {
            line.style.color = "#2ec4b6";
        } else if (type === "error") {
            line.style.color = "#e63946";
        } else {
            line.style.color = "#cbd5e1";
        }

        line.innerText = `[${time}] ${text}`;
        consoleBox.appendChild(line);
        consoleBox.scrollTop = consoleBox.scrollHeight;
    }

    async function loadQueue() {
        try {
            const resp = await fetch("/api/queue");
            const data = await resp.json();
            if (data && data.posts) {
                renderQueue(data.posts);
            }
        } catch (e) {
            console.error("قطار لوڈ کرنے میں خرابی", e);
        }
    }

    function renderQueue(posts) {
        if (!posts || posts.length === 0) {
            queueContainer.innerHTML = '<div style="color: #94a3b8; text-align:center; padding: 20px;">قطار میں کوئی پوسٹ موجود نہیں ہے۔ برائے مہربانی "روزانہ آڈٹ شروع کریں" پر کلک کریں۔</div>';
            return;
        }

        queueContainer.innerHTML = "";
        posts.forEach(p => {
            const isQuiz = p.post_type === "QUIZ";
            const item = document.createElement("div");
            item.className = `queue-item ${isQuiz ? 'quiz' : 'poll'}`;

            let optionsHtml = "";
            if (p.options) {
                optionsHtml = '<div class="queue-options">';
                p.options.forEach(opt => {
                    const isCorrect = isQuiz && p.correct_answer && opt.trim() === p.correct_answer.trim();
                    optionsHtml += `<div class="queue-option ${isCorrect ? 'correct' : ''}">${opt} ${isCorrect ? '✓' : ''}</div>`;
                });
                optionsHtml += '</div>';
            }

            item.innerHTML = `
                <div class="queue-item-header">
                    <div>
                        <span class="queue-badge ${isQuiz ? 'badge-quiz' : 'badge-poll'}">${isQuiz ? 'کوئز (Quiz)' : 'ٹیکسٹ پول (Poll)'}</span>
                        <span class="queue-badge badge-scheduled" style="margin-right: 6px;">${p.status}</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 0.8rem;">${p.target_date} | ${p.scheduled_time}</div>
                </div>
                <div class="queue-question">${p.question_text}</div>
                ${optionsHtml}
                ${p.source_reference ? `<div style="font-size: 0.8rem; color: #38bdf8; margin-top: 6px;">📖 حوالہ: ${p.source_reference}</div>` : ''}
            `;
            queueContainer.appendChild(item);
        });
    }

    // ابتدائی لوڈنگ
    loadQueue();
    appendConsole("Agent AM سسٹم فعال ہے اور جاب شیڈولر تیار ہے۔ خوش آمدید!", "success");
});
